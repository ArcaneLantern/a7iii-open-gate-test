"""A7 III (ILCE-7M3, firmware 4.04) kit 1 v2: service-mode file check. No camera file, setting or memory is written.

v2 (m3kit1_v2, 2026-11-26). The v1 run on the first tester's camera logged in and read the product information, but
the first file read answered 0x10000004. The 4.04 libJiritsu.so explains this (a7m3_map M3-F030). Every file command
mounts the service work partition /dev/nflasha6 on /tmp/jiritsu, and only Sony's own Jiritsu MOUNT command (0x4002)
creates that folder. The A7 IV kits never needed MOUNT, so v1 never sent it. v2 sends MOUNT before the reads and
always sends its unmount form afterwards, which unmounts the partition and removes the folder again.

What it does, in one service session (camera in USB Mass Storage mode):
  1. switches the camera into service mode and logs in with PMCA-RE's public keys (as for the A7 IV / A7S III kits);
  2. READ_HASP (product information);
  3. Jiritsu MOUNT, area 0: creates /tmp/jiritsu if missing and mounts /dev/nflasha6 there (Sony's service step);
  4. reads these files, one after another, and compares each with the 4.04 update (size + SHA-256):
       /usr/share/pmbp/DeviceInfo.xml   known answer: if it differs or fails, nothing more is read
       /usr/lib/libJiritsu.so           the library that implements the service file commands
       /usr/lib/libsencore.so           the service-mode library
       /usr/codec/vcd_firmware.bin      the video codec firmware
       /system/av-cam.bin               the imaging/recording program (18 MB)
       /setting/DmmConfig.bin           memory configuration (optional: may be missing)
       /proc/cpuinfo, /proc/iomem       expected empty (optional)
  5. always: Jiritsu MOUNT, unmount form (unmounts /dev/nflasha6 and removes /tmp/jiritsu);
  6. always sends the stop request.

Only four service commands can leave the PC: READ_HASP, Jiritsu MOUNT (exactly the two payloads above), SET_FILE_PATH
(for the paths above only) and GET_FILE2. The guards in CT1_usb_first_contact/ct1_common.py refuse anything else
before a byte is sent: file write, delete, format, firmware, settings and memory commands. MOUNT changes one thing on
the camera for the length of the run: the empty folder /tmp/jiritsu exists and the work partition is mounted there.
No settings backup is read (it would carry personal data).

  python -I -B m3_check.py --dry-run                    list exactly what would be sent (simulated camera)
  python -I -B m3_check.py --selftest                   run the checks against the simulated camera
  python -I -B m3_check.py --list                       show which Sony USB devices libusb sees; sends nothing
  python -I -B m3_check.py --go --firmware-shown 4.04   the real run

Results: windows/camera_private/M3K1v2_<time>_check/ (manifest.json, transcript.jsonl, small files). Large files
are not saved, only their size and SHA-256.
"""
import argparse
import contextlib
import hashlib
import io
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "CT1_usb_first_contact"))
import ct1_common as c                 # noqa: E402  guards, session log, pinned PMCA-RE
import ct1_stage2_service as s2        # noqa: E402  connect(), service_session(), libusb_devices()

KIT = "m3kit1_v2"
TEST = "M3K1v2"
EXPECTED_MODEL = "ILCE-7M3"
EXPECTED_FIRMWARE = "4.04"
EXPECTED = json.loads((HERE / "expected_404.json").read_text(encoding="utf-8"))["files"]
c.PREDICTIONS = HERE / "predictions.json"       # the manifest records this kit's predictions
KEEP_MAX = 1 << 20                              # files up to 1 MB are saved; larger ones are hashed only

# (camera path, required, known answer)
FILES = (
    ("/usr/share/pmbp/DeviceInfo.xml", True, True),
    ("/usr/lib/libJiritsu.so", True, False),
    ("/usr/lib/libsencore.so", True, False),
    ("/usr/codec/vcd_firmware.bin", True, False),
    ("/system/av-cam.bin", True, False),
    ("/setting/DmmConfig.bin", False, False),
    ("/proc/cpuinfo", False, False),
    ("/proc/iomem", False, False),
)

# libJiritsu.so cmd_mount 0x58cc reads the area byte (+0x1c) and the action byte (+0x1d), M3-F030.
# Area 0 = the work partition /dev/nflasha6 on /tmp/jiritsu. Area 1 (the memory card) is never sent.
MOUNT_WORK_AREA = b"\x00\x00"       # create /tmp/jiritsu if missing, mount /dev/nflasha6 there
UNMOUNT_WORK_AREA = b"\x00\x01"     # unmount /dev/nflasha6, remove /tmp/jiritsu
WORK_AREA_UNMOUNTED = 0x10000004    # adj_cmd_get_file2: sys_mount("/dev/nflasha6", "/tmp/jiritsu") failed


def wire(path):
    """The path as the file commands expect it: relative to /tmp/jiritsu."""
    return b"../.." + path.encode("ascii")


PATHS = tuple(wire(p) for p, _r, _k in FILES)

# The complete list of service packets this kit may send: (packet type, category, code) -> (name, payload test).
# Category 0x1001 codes are the A7 III's own (libsencore routing rows, a7m3_map M3-F027/F030): 0x4002 MOUNT,
# 0x400F SET_FILE_PATH, 0x4011 GET_FILE2. The write (0x4010), delete (0x4012), format (0x4003) and every other
# Jiritsu command are not on the list.
RULES = {
    (c.PFUNC_PRODUCT_INFO, 0x0000, 0x001F): ("READ_HASP", lambda p: p == b"\x00"),
    (c.PFUNC_ADJUST, 0x1001, 0x4002): ("JIRITSU_MOUNT", lambda p: p in (MOUNT_WORK_AREA, UNMOUNT_WORK_AREA)),
    (c.PFUNC_ADJUST, 0x1001, 0x400F): ("SET_FILE_PATH", lambda p: p[:1] == b"\x00" and p[1:] in PATHS),
    (c.PFUNC_ADJUST, 0x1001, 0x4011): ("GET_FILE2", lambda p: p == b"\x00\xff\x00"),
}


def safe_name(path):
    return path.strip("/").replace("/", "_")


def read_file(camera, path):
    """SET_FILE_PATH then GET_FILE2. Returns (status, payload)."""
    camera._sendAdjustControlPacket(0x1001, 0x400F, b"\x00" + wire(path))
    answer = camera._sendAdjustControlPacket(0x1001, 0x4011, b"\x00\xff\x00")
    status = struct.unpack_from("<I", answer)[0] if len(answer) >= 4 else None
    return status, answer[4:]


def jiritsu_mount(session, camera, payload, label):
    """Send Jiritsu MOUNT with one of the two listed payloads and record the answer. Never raises on a camera error:
    the reads that follow (or the stop request) are what decide the run."""
    record = session.results[label] = {"payload": payload.hex()}
    try:
        answer = camera._sendAdjustControlPacket(0x1001, 0x4002, payload)
    except c.GuardRefusal:
        raise
    except Exception as exc:
        record["error"] = "%s: %s" % (type(exc).__name__, exc)
        session.say("  %s: no clean answer (%s)" % (label, record["error"]))
        return record
    record["reply"] = answer[:16].hex()
    record["status"] = struct.unpack_from("<I", answer)[0] if len(answer) >= 4 else None
    session.say("  %s answered %s" % (label, record["reply"] or "with no data"))
    return record


def read_all(session, camera, expected):
    rows = session.results["files"] = []
    for path, required, known in FILES:
        session.say("Reading %s" % path)
        row = {"path": path, "required": required}
        rows.append(row)
        try:
            status, data = read_file(camera, path)
        except c.GuardRefusal:
            raise
        except Exception as exc:
            row["error"] = "%s: %s" % (type(exc).__name__, exc)
            session.say("  no answer: %s" % row["error"])
            raise c.StopTest("a file read got no answer; stopping (nothing is retried)")
        row.update(status=status, bytes=len(data))
        if status != 0:
            detail = "truncated status word" if status is None else "GET_FILE2 status 0x%08x" % status
            if status == WORK_AREA_UNMOUNTED:
                detail += " (the work partition /dev/nflasha6 could not be mounted on /tmp/jiritsu)"
            row["error"] = detail
            session.say("  %s; file contents unverified" % detail)
            if known:
                session.results["verdict"] = "UNVERIFIED: known-answer read failed: %s" % detail
                raise c.StopTest("known-answer read failed: %s; firmware identity unverified" % detail)
            continue
        digest = hashlib.sha256(data).hexdigest()
        row["sha256"] = digest
        want = expected.get(path)
        if want:
            row["matches_404"] = (len(data), digest) == (want["bytes"], want["sha256"])
        if data and len(data) <= KEEP_MAX:
            session.save_bytes("file_%s.bin" % safe_name(path), data)
        session.say("  status %s, %d bytes, SHA-256 %s%s" % (
            status, len(data), digest[:16],
            "" if want is None else ("  = 4.04" if row.get("matches_404") else "  DIFFERS from 4.04")))
        if known and not row.get("matches_404"):
            raise c.StopTest("the known-answer file %s does not match the 4.04 update; nothing more is read" % path)
    required = [r for r in rows if r["required"]]
    if any("error" in r for r in required):
        verdict = "UNVERIFIED: required file read failed: %s" % ", ".join(r["path"] for r in required if "error" in r)
    elif all(r.get("matches_404") for r in required):
        verdict = "4.04 CONFIRMED: every required file equals the 4.04 update"
    else:
        verdict = "NOT MATCHING: %s" % ", ".join(r["path"] for r in required if not r.get("matches_404"))
    session.results["verdict"] = verdict
    session.say("Verdict: " + verdict)


def body(session, camera, expected):
    hasp = camera.readHasp()
    session.save_bytes("hasp.bin", hasp)
    session.results["hasp_bytes"] = len(hasp)
    session.say("Mounting the service work area (Jiritsu MOUNT: /dev/nflasha6 on /tmp/jiritsu)")
    jiritsu_mount(session, camera, MOUNT_WORK_AREA, "mount")
    try:
        read_all(session, camera, expected)
    finally:
        session.say("Unmounting the service work area and removing /tmp/jiritsu (Jiritsu MOUNT, unmount form)")
        jiritsu_mount(session, camera, UNMOUNT_WORK_AREA, "unmount")


# ------------------------------------------------------------ simulated camera

def stand_in_files():
    """Files for the simulated camera. In the analysis tree the real 4.04 files are used; in the published kit
    (no firmware bytes shipped) stand-ins of the right size are generated and their hashes used as 'expected'."""
    import os
    ext = Path(os.environ.get("M3_EXTRACTED", HERE.parents[1] / "work" / "extracted" / "a7m3_404"))
    files, expected = {}, dict(EXPECTED)
    for path, _r, _k in FILES:
        want = EXPECTED.get(path)
        if want is None:
            files[wire(path)] = b""
            continue
        real = ext / want["from_update"]
        if real.is_file():
            files[wire(path)] = real.read_bytes()
        else:
            seed = hashlib.sha256(path.encode()).digest()
            data = (seed * (want["bytes"] // len(seed) + 1))[:want["bytes"]]
            files[wire(path)] = data
            expected[path] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    return files, expected


def a7m3_senser(files, mount_ok=True, mount_error=False):
    """The service device as the 4.04 libJiritsu behaves (M3-F030): file reads answer 0x10000004 until Jiritsu
    MOUNT has mounted the work partition. mount_ok=False: the partition will not mount. mount_error=True: MOUNT gets
    a packet-level error."""
    import ct1_sim

    class A7m3Senser(ct1_sim.SimDriver):
        def __init__(self):
            super().__init__("senser", files=files, rules=RULES)
            self.mounted = False
            self.mount_calls = []

        def _handle(self, pfunc, body):
            try:
                name = c.classify_service_packet(pfunc, body, self.rules)
            except c.GuardRefusal:
                return super()._handle(pfunc, body)
            if name == "JIRITSU_MOUNT":
                self.mount_calls.append(bytes(body[4:]))
                if bytes(body[4:]) == MOUNT_WORK_AREA:
                    if mount_error:
                        return 5, b""
                    self.mounted = mount_ok
                    return 0, struct.pack("<I", 0 if mount_ok else WORK_AREA_UNMOUNTED)
                self.mounted = False
                return 0, struct.pack("<I", 0)
            if name == "GET_FILE2" and not self.mounted:
                return 0, struct.pack("<I", WORK_AREA_UNMOUNTED)
            return super()._handle(pfunc, body)

    return A7m3Senser()


def sim_run(files, expected, **camera):
    """One full run against the simulated camera. Returns (session, msc driver, service driver)."""
    import ct1_sim
    c.use_pmca()
    session = c.Session("sim", write=False, test=TEST)
    msc = ct1_sim.SimDriver("msc")
    senser = a7m3_senser(files, **camera)
    with contextlib.redirect_stdout(io.StringIO()):
        s2.phase_a(session, msc)
        try:
            s2.service_session(session, senser, lambda cam: body(session, cam, expected), RULES)
        except c.StopTest as exc:
            session.results["stopped"] = str(exc)
    return session, msc, senser


MOUNT_TEXT = {MOUNT_WORK_AREA.hex(): "mount /dev/nflasha6 on /tmp/jiritsu",
              UNMOUNT_WORK_AREA.hex(): "unmount /dev/nflasha6 and remove /tmp/jiritsu"}


def dry_run_lines():
    files, expected = stand_in_files()
    session, msc, senser = sim_run(files, expected)
    if msc.unexpected or senser.unexpected:
        raise AssertionError("simulated camera saw something off the list: %r" % (msc.unexpected + senser.unexpected))
    lines, device, auth = [], None, 0

    def flush():
        nonlocal auth
        if auth:
            lines.append("  %d authentication packets of 516 bytes on bulk endpoint 0 "
                         "(PMCA-RE SonySenserAuthDevice.authenticate)" % auth)
            auth = 0

    for e in session.events:
        if e.get("dev") and e["dev"] != device:
            flush()
            device = e["dev"]
            lines.append("To the mass-storage device (after SCSI TEST UNIT READY and INQUIRY):" if device == "msc"
                         else "To the service device:")
        if e["kind"] == "usb_vendor_out":
            flush()
            lines.append("  vendor request out: request %d, value %s, index %s, no data  (%s)"
                         % (e["request"], e["value"], e["index"], e["name"]))
        elif e["kind"] == "usb_out" and e["bytes"] == 516:
            auth += 1
        elif e["kind"] == "service_out":
            flush()
            b = bytes.fromhex(e["hex"])
            extra = ""
            if e["name"] == "SET_FILE_PATH":
                extra = ": " + b[5:].decode()
            elif e["name"] == "JIRITSU_MOUNT":
                extra = ": " + MOUNT_TEXT[b[4:].hex()]
            lines.append("  service packet type 0x%02x, body %s  (%s%s)" % (
                e["pfunc"], b[:8].hex(" ") + (" ..." if len(b) > 8 else ""), e["name"], extra))
    flush()
    return lines, session


def selftest():
    from unittest.mock import Mock
    failures = []

    def check(name, ok, detail=""):
        print("%-66s %s%s" % (name, "pass" if ok else "FAIL", ("  " + detail) if detail and not ok else ""))
        if not ok:
            failures.append(name)

    def sent(session):
        return [(e["name"], bytes.fromhex(e["hex"])[4:]) for e in session.events if e["kind"] == "service_out"]

    def ends_cleanly(session, senser):
        vendor = [e["name"] for e in session.events if e["kind"] == "usb_vendor_out"]
        return (senser.mount_calls == [MOUNT_WORK_AREA, UNMOUNT_WORK_AREA] and vendor[-1:] == ["STOP_SENSER"]
                and sent(session)[-1] == ("JIRITSU_MOUNT", UNMOUNT_WORK_AREA))

    files, expected = stand_in_files()
    # 1. normal run
    session, msc, senser = sim_run(files, expected)
    rows = session.results.get("files", [])
    check("normal run reads all %d files" % len(FILES), len(rows) == len(FILES), str(session.results.get("stopped")))
    check("normal run verdict is 4.04 CONFIRMED", session.results.get("verdict", "").startswith("4.04 CONFIRMED"))
    check("simulated camera saw nothing off the list", not msc.unexpected and not senser.unexpected)
    names = [n for n, _p in sent(session)]
    check("only READ_HASP / MOUNT / SET_FILE_PATH / GET_FILE2 were sent",
          set(names) <= {"READ_HASP", "JIRITSU_MOUNT", "SET_FILE_PATH", "GET_FILE2"}
          and names.count("GET_FILE2") == len(FILES) and names.count("JIRITSU_MOUNT") == 2)
    check("MOUNT comes right after READ_HASP, before any file read",
          sent(session)[:2] == [("READ_HASP", b"\x00"), ("JIRITSU_MOUNT", MOUNT_WORK_AREA)])
    check("unmount is the last packet, then the stop request", ends_cleanly(session, senser))
    # 2. the work partition will not mount -> v1's 0x10000004, stop, still unmount + stop
    session, _m, senser = sim_run(files, expected, mount_ok=False)
    row = (session.results.get("files") or [{}])[0]
    check("partition will not mount: 0x10000004 stops after the first read",
          len(session.results.get("files", [])) == 1 and row.get("status") == WORK_AREA_UNMOUNTED
          and "unverified" in session.results.get("stopped", "")
          and session.results.get("mount", {}).get("status") == WORK_AREA_UNMOUNTED)
    check("  ... and still unmounts and sends the stop request", ends_cleanly(session, senser))
    # 3. MOUNT gets a packet-level error -> recorded, reads fail, still unmount + stop
    session, _m, senser = sim_run(files, expected, mount_error=True)
    check("MOUNT packet error is recorded and the run ends unverified",
          "error" in session.results.get("mount", {}) and "unverified" in session.results.get("stopped", ""))
    check("  ... and still unmounts and sends the stop request", ends_cleanly(session, senser))
    # 4. known answer differs -> stop after the first file
    bad = dict(files)
    bad[wire(FILES[0][0])] = b"<not the 4.04 file/>"
    session, _m, senser = sim_run(bad, expected)
    check("known-answer mismatch stops after the first read",
          len(session.results.get("files", [])) == 1 and "known-answer" in session.results.get("stopped", ""))
    check("  ... and still unmounts and sends the stop request", ends_cleanly(session, senser))
    # 5. status-only or short replies leave identity unverified; MOUNT and unmount still sent
    for answer in (struct.pack("<I", WORK_AREA_UNMOUNTED), b"\x00\x00"):
        probe = Mock()
        probe.readHasp.return_value = b""
        probe._sendAdjustControlPacket.side_effect = [bytes(4), bytes(4), answer, bytes(4)]
        session = c.Session("sim", write=False, test=TEST)
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                body(session, probe, expected)
            except c.StopTest as exc:
                session.results["stopped"] = str(exc)
        row = session.results["files"][0]
        calls = probe._sendAdjustControlPacket.call_args_list
        check("status-only/short reply %s leaves identity unverified" % answer.hex(),
              "unverified" in session.results.get("stopped", "")
              and "error" in row and "matches_404" not in row and "sha256" not in row
              and len(calls) == 4 and calls[-1].args == (0x1001, 0x4002, UNMOUNT_WORK_AREA))
    # 6. the USB link fails during a read -> stop, unmount still attempted
    probe = Mock()
    probe.readHasp.return_value = b""
    probe._sendAdjustControlPacket.side_effect = [bytes(4), OSError("cable pulled"), bytes(4)]
    session = c.Session("sim", write=False, test=TEST)
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            body(session, probe, expected)
        except c.StopTest as exc:
            session.results["stopped"] = str(exc)
    calls = probe._sendAdjustControlPacket.call_args_list
    check("failed read: run stops and the unmount is still attempted",
          "no answer" in session.results.get("stopped", "") and calls[-1].args == (0x1001, 0x4002, UNMOUNT_WORK_AREA))
    # 7. a required file differs -> all read, verdict NOT MATCHING
    bad = dict(files)
    orig = files[wire("/system/av-cam.bin")]
    bad[wire("/system/av-cam.bin")] = orig[:-1] + bytes([orig[-1] ^ 0xFF])
    session, _m, _s = sim_run(bad, expected)
    check("av-cam difference gives NOT MATCHING", session.results.get("verdict", "").startswith("NOT MATCHING"))
    # 8. an optional file missing -> run continues
    miss = dict(files)
    del miss[wire("/setting/DmmConfig.bin")]
    session, _m, _s = sim_run(miss, expected)
    check("missing optional file: run continues to the end", len(session.results.get("files", [])) == len(FILES))
    # 9. the guard refuses everything else
    adj = lambda code, payload, cat=0x1001: struct.pack("<HH", cat, code) + payload   # noqa: E731
    for label, pfunc, data in (
            ("file write (0x4010)", c.PFUNC_ADJUST, adj(0x4010, b"\x00\xff\x00ab")),
            ("file delete (0x4012)", c.PFUNC_ADJUST, adj(0x4012, b"\x00\xff")),
            ("format (0x4003)", c.PFUNC_ADJUST, adj(0x4003, b"\x00")),
            ("MOUNT of the memory card (area 1)", c.PFUNC_ADJUST, adj(0x4002, b"\x01\x00")),
            ("MOUNT with another action byte", c.PFUNC_ADJUST, adj(0x4002, b"\x00\x02")),
            ("MOUNT with an extra byte", c.PFUNC_ADJUST, adj(0x4002, b"\x00\x00\x00")),
            ("MOUNT with no payload", c.PFUNC_ADJUST, adj(0x4002, b"")),
            ("Jiritsu MODE (0x4001)", c.PFUNC_ADJUST, adj(0x4001, b"\x00")),
            ("Jiritsu START (0x4004)", c.PFUNC_ADJUST, adj(0x4004, b"\x00")),
            ("Jiritsu FIRMUP (0x4006)", c.PFUNC_ADJUST, adj(0x4006, b"\x00")),
            ("Jiritsu FACTORY (0x400e)", c.PFUNC_ADJUST, adj(0x400E, b"\x00")),
            ("backup read (0x603/5)", c.PFUNC_ADJUST, adj(0x0005, b"\x01", 0x0603)),
            ("SET_FILE_PATH to an unlisted path", c.PFUNC_ADJUST, adj(0x400F, b"\x00../../etc/passwd")),
            ("coprocessor debug group 0x60b", c.PFUNC_ADJUST, adj(0x0001, b"\x00", 0x060B)),
            ("memory dump packet type 0xff03", 0xFF03, struct.pack("<HH", 0x0000, 0x0000) + b"\x00")):
        try:
            c.classify_service_packet(pfunc, data, RULES)
            check("guard refuses %s" % label, False, "was allowed")
        except c.GuardRefusal:
            check("guard refuses %s" % label, True)
    # 10. dry-run listing
    lines, _session = dry_run_lines()
    text = "\n".join(lines)
    check("dry run lists only listed paths", all(("SET_FILE_PATH: ../.." + p) in text for p, _r, _k in FILES))
    check("dry run shows the mount and the unmount", text.count("JIRITSU_MOUNT") == 2
          and text.index(MOUNT_TEXT["0000"]) < text.index("SET_FILE_PATH") < text.index(MOUNT_TEXT["0001"]))
    print("\n%d failed" % len(failures))
    return not failures


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--selftest", action="store_true")
    mode.add_argument("--list", action="store_true")
    mode.add_argument("--go", action="store_true")
    parser.add_argument("--firmware-shown", help="the version the camera's menu shows (must be 4.04)")
    args = parser.parse_args()

    if args.dry_run:
        lines, _session = dry_run_lines()
        print("Kit 1 v2 would send, in this order (simulated camera):")
        print("\n".join(lines))
        return
    if args.selftest:
        sys.exit(0 if selftest() else 1)
    if args.list:
        c.use_pmca()
        session = c.Session("list", write=False, test=TEST)
        c.print_pnp(session, "now")
        try:
            msc, senser = s2.libusb_devices()
        except c.StopTest as exc:
            print(exc)
            return
        print("libusb sees: %d Sony mass-storage device(s) %s, %d Sony service device(s) %s"
              % (len(msc), ["%04x:%04x" % (d.idVendor, d.idProduct) for d in msc],
                 len(senser), ["%04x:%04x" % (d.idVendor, d.idProduct) for d in senser]))
        print("Nothing was sent to any device.")
        return
    if (args.firmware_shown or "").strip() != EXPECTED_FIRMWARE:
        raise SystemExit("This kit is for an %s on firmware %s only. Pass --firmware-shown with the version the "
                         "camera's menu shows (MENU > Setup > Version)." % (EXPECTED_MODEL, EXPECTED_FIRMWARE))
    with c.Session("check", test=TEST) as session:
        session.results.update(kit=KIT, firmware_shown_on_camera=args.firmware_shown)
        inner = s2.connect(session)
        model = (session.results.get("msc_inquiry") or {}).get("model")
        if model is not None:
            session.say("Mass-storage INQUIRY model text: %r" % model)
        try:
            s2.service_session(session, inner, lambda cam: body(session, cam, EXPECTED), RULES)
        finally:
            import time
            time.sleep(3)
            c.print_pnp(session, "after the stop request")
        print("No camera file, setting or memory was written. The service work folder was mounted and removed again.")


if __name__ == "__main__":
    main()
