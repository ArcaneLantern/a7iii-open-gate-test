"""A7 III (ILCE-7M3, firmware 4.04) kit 2 (m3kit2_v3): open-gate tests, and a debug dump.

v3 (2026-11-26), after the second run on a tester's camera (a7m3_map FINDINGS M3-F039..F041): v2's test 1 ran with no
fault; v2's test 2 restarted the camera when movie mode started. The restart was the firmware's own forced stop
("S-Ele Refresh ng force exception") after ten refreshes of a lost output sync, and it put the 4.04 bytes back by
itself. Cause as far as the firmware shows it: test 2 made the front-end records 624 lines taller but left the
camera-core timing pair of that drive at the stock 3436 lines. v3 moves the timing pair with the records, adds two
smaller heights, and the dump now also copies the camera's application log.

Six steps, each one service session that loads one small helper library on the camera (helper/m3og.c, design og_m3_v2
of a7m3_map; modding/OG_M3_V2.md there):

  dump      READ-ONLY. Kernel and memory facts, the kernel log and the application log, where av-cam sits in memory
            (checked against the 4.04 file), what every byte of the design holds now (stock / test 1..4), and copies
            of the sensor, front-end and timing tables. Run it first, and straight after any restart.
  test1     WRITES 7 bytes in the camera's RAM: the sensor register list of the 4K 24p/25p full-frame mode reads the
            whole sensor height (4036 rows from row 61) instead of the 16:9 band (3412 rows from row 373). The front end
            is left stock, so the recorded 16:9 picture is the TOP band of the sensor: a shift, not yet a taller picture.
            Ran on a camera with no fault.
  test2     WRITES the sensor window, both front-end records of that mode (heights +624, vertical scaler step 6888) and
            the camera-core timing pair (2030 line pairs; cycle 726, or 696 in the 50 system): the whole 3:2 sensor
            height recorded squeezed into the stock 3840x2160 file (stretch it vertically by 1.185). The line rate is
            15 % (18 %) above stock: the camera may not keep up, in which case it restarts and is stock again.
  test3     The same three parts for half the extra height: 3724 rows, picture 3688 rows (stretch 1.092), line rate
            6 % (9 %) above stock.
  test4     The same for a quarter: 3568 rows, picture 3532 rows (stretch 1.046), line rate 2 % (5 %) above stock.
  putback   WRITES the 4.04 bytes back wherever a test changed them. A restart or a battery pull does the same.

Nothing is written to flash except Sony's own service step: the library itself is written to the service work
partition (/tmp/jiritsu/libJit.so, which is how the camera loads it) and deleted again in the same session. The helper
writes its result to the RAM tmpfs /tmp_network (else /tmp/jiritsu), from where it is read back and deleted.

What one session sends, in order (camera in USB Mass Storage mode):
  1. service-mode switch and login with PMCA-RE's public keys (as kit 1);
  2. READ_HASP; Jiritsu MOUNT 00 00 (creates /tmp/jiritsu and mounts the work partition, kit 1 v2);
  3. known-answer read of DeviceInfo.xml (must equal 4.04, else nothing more);
  4. checks: no libJit.so on the partition (this kit's own one from an aborted run is deleted), no result file left
     (an old one is saved and deleted), no /tmp/jbusy;
  5. SET_FILE_PATH /tmp/jiritsu/libJit.so, SET_FILE2 with the pinned library: the camera writes it and loads it, which
     runs the helper once;
  6. FILE_DELETE2 of the library, and a read that confirms it is gone;
  7. the helper's result is read, saved and deleted;
  8. always: Jiritsu MOUNT 00 01 (unmount, remove /tmp/jiritsu); always the stop request.

Only READ_HASP, Jiritsu MOUNT (two payloads), SET_FILE_PATH (listed paths only), GET_FILE2, SET_FILE2 (only the pinned
library, only onto /tmp/jiritsu/libJit.so, once) and FILE_DELETE2 (only the library and the result files) can leave
the PC; the guard refuses anything else before a byte is sent.

  python -I -B m3og.py --selftest                      simulated camera, every rule and failure path
  python -I -B m3og.py <step> --dry-run                exactly what <step> would send (simulated camera)
  python -I -B m3og.py --list                          which Sony USB devices libusb sees; sends nothing
  python -I -B m3og.py <step> --go --firmware-shown 4.04

Results: windows/camera_private/M3K2_<time>_<step>/ (manifest.json, transcript.jsonl, m3og_result.txt; the dump also
klog.txt, alog.txt and one .bin per memory range).
"""
import argparse
import contextlib
import hashlib
import io
import json
import os
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "CT1_usb_first_contact"))
import ct1_common as c                 # noqa: E402  guards, session log, pinned PMCA-RE
import ct1_stage2_service as s2        # noqa: E402  connect(), libusb_devices()

KIT = "m3kit2_v3"
TEST = "M3K2"
EXPECTED_MODEL = "ILCE-7M3"
EXPECTED_FIRMWARE = "4.04"
HELPER = HERE / "helper"
c.PREDICTIONS = HERE / "predictions.json"
KNOWN = json.loads((HERE.parent / "K1_readonly" / "expected_404.json").read_text(encoding="utf-8"))["files"]["/usr/share/pmbp/DeviceInfo.xml"]

# step -> (library, SHA-256, writes?, what it does)
STEPS = {
    "dump": ("libJit_m3og_dump.so", "06a82e7e23447c36929a6df9acb3458b6e85366e93bbc07729ac00d9734bf112", False,
             "read-only dump: facts, kernel and application log, where av-cam is, what the design's bytes hold, the tables"),
    "test1": ("libJit_m3og_test1.so", "0c456507951e93034f6c9211314713f8f53e0cfe544644250a390e13e9e97d87", True,
              "TEST 1: the 4K 24p/25p full-frame sensor mode reads the whole sensor height (7 bytes)"),
    "test2": ("libJit_m3og_test2.so", "d6e8d5f1b050f84994b1944f24e838e5674fae7f7b4a0e9126ce30733340d095", True,
              "TEST 2: sensor + front end + timing: the whole 3:2 height squeezed into the stock 4K file"),
    "test3": ("libJit_m3og_test3.so", "15073da4f7e73456da4c2db94e1be282f8466509880279bbabe67cdd5045a53f", True,
              "TEST 3: as test 2 for half the extra height (picture 3688 rows)"),
    "test4": ("libJit_m3og_test4.so", "5b07b3e3d6be20a562b11c37473794f29bf1934df54dbf321d17e517389b4d7e", True,
              "TEST 4: as test 2 for a quarter of the extra height (picture 3532 rows)"),
    "putback": ("libJit_m3og_putback.so", "4e19f3407be1200e616d5c9244cff04717fcd4b464685936ba2fc3b507ef8b78", True,
                "PUT BACK: the 4.04 bytes again wherever a test changed them"),
}
PINNED = {sha for _n, sha, _w, _t in STEPS.values()}
LIB_MAX = 65520                                  # one upload packet (the A7 IV client's bound)

SET_FILE_PATH, SET_FILE2, GET_FILE2, FILE_DELETE2, MOUNT = 0x400F, 0x4010, 0x4011, 0x4012, 0x4002
MOUNT_WORK_AREA, UNMOUNT_WORK_AREA = b"\x00\x00", b"\x00\x01"
KNOWN_PATH = b"../../usr/share/pmbp/DeviceInfo.xml"
LIB_PATH = b"/tmp/jiritsu/libJit.so"             # must be exactly this string: adj_cmd_set_file2 compares it, then dlopen
RESULT_PATHS = (b"../../tmp_network/m3og_result.txt", b"m3og_result.txt")   # /tmp_network (RAM tmpfs), else /tmp/jiritsu (the work partition)
BUSY_PATH = b"../../tmp/jbusy"
PATHS = (KNOWN_PATH, LIB_PATH, BUSY_PATH) + RESULT_PATHS

ST_OK, ST_LOAD_FAILED, ST_UNMOUNTED, ST_NO_FILE, ST_BUSY = 0, 0x10000000, 0x10000004, 0x10000006, 0x10000011
STATUS_TEXT = {ST_OK: "ok", ST_LOAD_FAILED: "written, but the camera could not load it", ST_UNMOUNTED: "work partition not mounted",
               ST_NO_FILE: "no such file", ST_BUSY: "refused: /tmp/jbusy exists", 0x10000008: "open failed",
               0x10000009: "write error", 0x1000000A: "read error", 0x10000201: "request refused as malformed"}


def text(status):
    return "no status" if status is None else "0x%08x (%s)" % (status, STATUS_TEXT.get(status, "not a status this kit knows"))


def library(step):
    name, sha, _w, _t = STEPS[step]
    path = HELPER / name
    if not path.is_file():
        raise SystemExit("%s is missing from this kit. Nothing was sent." % name)
    data = path.read_bytes()
    if c.sha256(data) != sha or not 0 < len(data) <= LIB_MAX:
        raise SystemExit("%s is not the pinned build (SHA-256 %s, %d bytes). Nothing was sent." % (name, c.sha256(data), len(data)))
    return data


def rules(lib):
    return {
        (c.PFUNC_PRODUCT_INFO, 0x0000, 0x001F): ("READ_HASP", lambda p: p == b"\x00"),
        (c.PFUNC_ADJUST, 0x1001, MOUNT): ("JIRITSU_MOUNT", lambda p: p in (MOUNT_WORK_AREA, UNMOUNT_WORK_AREA)),
        (c.PFUNC_ADJUST, 0x1001, SET_FILE_PATH): ("SET_FILE_PATH", lambda p: p[:1] == b"\x00" and p[1:] in PATHS),
        (c.PFUNC_ADJUST, 0x1001, GET_FILE2): ("GET_FILE2", lambda p: p == b"\x00\xff\x00"),
        (c.PFUNC_ADJUST, 0x1001, SET_FILE2): ("SET_FILE2", lambda p: p == b"\x00\xff\x00" + lib and c.sha256(p[3:]) in PINNED),
        (c.PFUNC_ADJUST, 0x1001, FILE_DELETE2): ("FILE_DELETE2", lambda p: p == b"\x00\xff"),
    }


class Guard(c.ServiceGuard):
    """CT1's guard plus the rules a library upload needs: the write only onto the library path and only once; deletes only
    of the library or a result file; the one large packet only of the library's exact size."""

    def __init__(self, device, session, rule_list, lib):
        super().__init__(device, session, rule_list)
        self._big = len(lib) + 7
        self.writes = 0

    def _send(self, pFunc, data, _oData):
        if len(data) > 0x1000 and len(data) != self._big:
            raise c.GuardRefusal("a %d-byte service packet that is not the pinned library" % len(data))
        device = self._device
        header = struct.pack(c.SENSER_HEADER, len(data), pFunc, device._sequence, 0, 0, 0, 0)
        device.driver.write(header + bytes(data))                      # one write, as for the A7 IV kits
        response, out = c.read_service_answer(device.driver, device._sequence, self.session.log)
        device._sequence += 1
        return response, out

    def send(self, pFunc, data, oData=None):
        name = c.classify_service_packet(pFunc, data, self.rules)      # raises before any write
        if name == "SET_FILE2":
            if self._path_set != LIB_PATH:
                raise c.GuardRefusal("SET_FILE2 when the path selected just before is not %s" % LIB_PATH.decode())
            if self.writes:
                raise c.GuardRefusal("a second file write in one session")
            self.writes += 1
        if name == "FILE_DELETE2" and self._path_set not in (LIB_PATH,) + RESULT_PATHS:
            raise c.GuardRefusal("FILE_DELETE2 when the path selected just before is not the library or a result file")
        return super().send(pFunc, data, oData)


def service_session(session, inner, body, lib):
    """As kit 1's service session, with this kit's guard. The stop request is always sent."""
    from pmca.usb.sony import SonySenserAuthDevice, SonySenserCamera, SonySenserDevice
    import ct1_compare
    driver = c.GuardedDriver(inner, session, "senser")
    session.results["service_usb_id"] = "%04x:%04x" % driver.getId()
    auth = SonySenserAuthDevice(driver)
    session.say("Authenticating")
    auth.start()
    try:
        try:
            auth.authenticate()
        finally:
            session.results["auth_service"] = ct1_compare.auth_summary(session.events, "senser")
        device = SonySenserDevice(driver)
        Guard(device, session, rules(lib), lib)
        body(SonySenserCamera(device))
    finally:
        auth.stop()
        session.say("Stop request sent")


# ------------------------------------------------------------ the steps

def command(camera, code, payload):
    answer = camera._sendAdjustControlPacket(0x1001, code, payload)
    if len(answer) < 4:
        return None, b""
    return struct.unpack_from("<I", answer)[0], answer[4:]


def select(camera, path):
    status, _ = command(camera, SET_FILE_PATH, b"\x00" + path)
    if status not in (None, ST_OK):
        raise c.StopTest("selecting %s: status %s" % (path.decode(), text(status)))


def read(camera, path):
    """(True, content) if the file is there, (False, b'') if the camera says it is not; anything else stops."""
    select(camera, path)
    status, data = command(camera, GET_FILE2, b"\x00\xff\x00")
    if status == ST_OK:
        return True, data
    if status == ST_NO_FILE:
        return False, b""
    raise c.StopTest("reading %s: status %s" % (path.decode(), text(status)))


def delete(session, camera, path, out, key):
    """Delete one file and confirm. Never raises for a camera answer: the outcome is recorded and said aloud."""
    rec = out[key] = {"path": path.decode()}
    try:
        select(camera, path)
        rec["status"], _ = command(camera, FILE_DELETE2, b"\x00\xff")
        rec["gone"] = read(camera, path)[0] is False
    except c.GuardRefusal:
        raise
    except Exception as exc:
        rec["error"] = "%s: %s" % (type(exc).__name__, exc)
    return rec


def jiritsu_mount(session, camera, payload, label):
    record = session.results[label] = {"payload": payload.hex()}
    try:
        answer = camera._sendAdjustControlPacket(0x1001, MOUNT, payload)
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


def body(session, camera, step, lib):
    out = session.results["k2"] = {"step": step, "library": STEPS[step][0], "library_bytes": len(lib),
                                   "library_sha256": c.sha256(lib), "library_sent": False}
    hasp = camera.readHasp()
    session.save_bytes("hasp.bin", hasp)
    session.say("Mounting the service work area (Jiritsu MOUNT)")
    jiritsu_mount(session, camera, MOUNT_WORK_AREA, "mount")
    try:
        steps(session, camera, step, lib, out)
    finally:
        session.say("Unmounting the service work area (Jiritsu MOUNT, unmount form)")
        jiritsu_mount(session, camera, UNMOUNT_WORK_AREA, "unmount")


def steps(session, camera, step, lib, out):
    there, data = read(camera, KNOWN_PATH)
    if not there or (len(data), c.sha256(data)) != (KNOWN["bytes"], KNOWN["sha256"]):
        raise c.StopTest("DeviceInfo.xml is not the 4.04 file (%s); nothing else is sent"
                         % ("the camera returned no file" if not there else "%d bytes, SHA-256 %s" % (len(data), c.sha256(data)[:16])))
    session.say("Known-answer read: DeviceInfo.xml equals the 4.04 file")
    there, data = read(camera, LIB_PATH)
    if there:
        if c.sha256(data) not in PINNED:
            raise c.StopTest("a libJit.so that is NOT one of this kit's libraries is on the service partition (%d bytes). "
                             "It is left alone and nothing was written." % len(data))
        session.say("This kit's own libJit.so from an earlier, interrupted run is on the partition; deleting it first")
        rec = delete(session, camera, LIB_PATH, out, "old_library_delete")
        if not rec.get("gone"):
            raise c.StopTest("the old library could not be deleted (%s); nothing was written" % rec)
    for k, path in enumerate(RESULT_PATHS):
        there, old = read(camera, path)
        if there:
            session.save_bytes("old_result_%d.txt" % k, old)
            session.say("An earlier result file was still on the camera (%d bytes): saved as old_result_%d.txt, deleting it" % (len(old), k))
            rec = delete(session, camera, path, out, "old_result_delete_%d" % k)
            if not rec.get("gone"):
                raise c.StopTest("the old result file could not be deleted; the helper would do nothing. Nothing was written.")
    if read(camera, BUSY_PATH)[0]:
        raise c.StopTest("/tmp/jbusy exists; the camera would refuse the library. Nothing was written.")
    session.say("Checks passed: no library, no result file, not busy")

    select(camera, LIB_PATH)
    session.say("Sending the library %s (%d bytes): the camera writes it and loads it" % (STEPS[step][0], len(lib)))
    out["library_sent"] = True
    status = None
    try:
        status, _ = command(camera, SET_FILE2, b"\x00\xff\x00" + lib)
    except c.GuardRefusal:
        out["library_sent"] = False
        raise
    except Exception as exc:
        out["write_error"] = "%s: %s" % (type(exc).__name__, exc)
        session.say("The write got no answer (%s)" % out["write_error"])
    out["write_status"] = status
    if "write_error" not in out:
        session.say("Write and load: status %s" % text(status))

    rec = delete(session, camera, LIB_PATH, out, "library_delete")       # always, once the library was sent
    if rec.get("gone"):
        session.say("Confirmed: /tmp/jiritsu/libJit.so is gone again")
    else:
        session.say("!! THE LIBRARY MAY STILL BE ON THE SERVICE PARTITION (%s). It is not loaded again by itself. Run this step "
                    "again: it deletes its own library first." % rec)
    if "write_error" in out:
        raise c.StopTest("the write got no answer; the result is not read")

    found = None
    for k, path in enumerate(RESULT_PATHS):
        there, result = read(camera, path)
        if there:
            found = (k, path, result)
            break
    out["result_found"] = None if not found else found[1].decode()
    if not found:
        raise c.StopTest("no result file: the helper did not create one (write status %s)" % text(status))
    _k, path, result = found
    session.save_bytes("m3og_result.txt", result)
    facts = out["result"] = parse_result(result, step)
    for name, blob in facts.pop("_ranges", {}).items():
        session.save_bytes("mem_%s.bin" % name, blob)
    for key, name in (("_klog", "klog.txt"), ("_alog", "alog.txt")):
        blob = facts.pop(key, None)
        if blob is not None:
            session.save_bytes(name, blob)
    rec = delete(session, camera, path, out, "result_delete")
    session.say("Result read (%d bytes) and %s" % (len(result), "deleted" if rec.get("gone") else "NOT deleted (%s)" % rec))
    say_result(session, facts)


def parse_result(data, step):
    """The facts of a helper result."""
    t = data.decode("utf8", "replace")
    lines = t.split("\n")
    pick = lambda start: next((ln for ln in lines if ln.startswith(start)), None)    # noqa: E731
    verdicts = [ln[8:] for ln in lines if ln.startswith("VERDICT ")]
    outcome = None
    if STEPS[step][2]:
        outcome = ("UNDO INCOMPLETE" if pick("!! UNDO INCOMPLETE") else "DONE" if pick("DONE: ") else "NOTHING TO DO" if pick("NOTHING TO DO")
                   else "NOT DONE" if pick("NOT DONE: ") else "UNKNOWN")
    blocks = {}
    for ln in lines:
        m = re.match(r"block (\S+) va (0x[0-9a-f]+) len (0x[0-9a-f]+) .*  (STOCK|TEST[1-4]|MIXED|OTHER)$", ln)
        if m:
            blocks.setdefault(m.group(1), []).append(m.group(4))
    facts = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "header": lines[0] if lines else "",
             "header_ok": bool(lines) and lines[0].startswith("m3og ") and ("level %s for ILCE-7M3 4.04" % step) in lines[0],
             "complete": any(ln.startswith("== done") for ln in lines[-3:]),
             "identity_same": sum(1 for ln in lines if ln.endswith("SAME as the 4.04 file")),
             "image_pages_live": [ln.split()[2] for ln in lines if ln.startswith("page va ") and "differs from 4.04" in ln],
             "identity_differs": sum(1 for ln in lines if ln.endswith("DIFFERS from the 4.04 file")),
             "tv_system": next((ln.split("tv system ", 1)[1].strip() for ln in lines if ln.startswith("slot 28 hmax ") and "tv system " in ln), None),
             "verdicts": verdicts, "outcome": outcome,
             "outcome_line": pick("DONE: ") or pick("NOTHING TO DO") or pick("NOT DONE: ") or pick("!! UNDO INCOMPLETE"),
             "blocks": blocks, "problems": [ln for ln in lines if ln.startswith("!!")]}
    cmd = re.search(r"== file /proc/cmdline\n(.*?)\n== end", t, re.S)
    facts["kernel_command_line"] = cmd.group(1).strip() if cmd else None
    ver = re.search(r"== file /proc/version\n(.*?)\n== end", t, re.S)
    facts["kernel_version"] = ver.group(1).strip() if ver else None
    ranges = {}
    for m in re.finditer(r"== mem (\S+) va (0x[0-9a-f]+) phys (0x[0-9a-f]+) len (0x[0-9a-f]+)\n(.*?)== end", t, re.S):
        hexes = "".join(ln.split(" ", 1)[1] for ln in m.group(5).strip().split("\n") if " " in ln and not ln.startswith("!!"))
        try:
            ranges["%s_%s" % (m.group(1), m.group(2))] = bytes.fromhex(hexes)
        except ValueError:
            pass
    if ranges:
        facts["_ranges"] = ranges
    for key in ("klog", "alog"):
        k = re.search(r"== %s phys \S+ len \S+\n(.*?)\n== (end|cut)" % key, t, re.S)
        if k:
            facts["_" + key] = k.group(1).encode("utf8", "replace")
            facts[key + "_bytes"] = len(facts["_" + key])
    return facts


def say_result(session, f):
    session.say("Helper result: header %s, %s, identity %d same / %d differ"
                % ("ok" if f["header_ok"] else "NOT as expected", "complete" if f["complete"] else "INCOMPLETE",
                   f["identity_same"], f["identity_differs"]))
    if f["image_pages_live"]:
        session.say("  %d of the first 16 image pages hold live data (reported only, not required): %s"
                    % (len(f["image_pages_live"]), " ".join(f["image_pages_live"])))
    if f.get("tv_system"):
        session.say("  TV system of the 4K full-frame drive: " + f["tv_system"])
    for v in f["verdicts"]:
        session.say("  VERDICT " + v)
    if f["outcome"]:
        session.say("  Outcome: %s  (%s)" % (f["outcome"], f["outcome_line"]))
    for p in f["problems"]:
        session.say("  " + p)


# ------------------------------------------------------------ simulated camera

def canned_result(step, state):
    """What the helper would report on a model camera when it cannot be emulated here (the kit ships no firmware).
    state: the design's state before the step ('stock', 'test1' .. 'test4'). Returns (text, new state)."""
    name = {"stock": "READY (stock)", **{"test%d" % n: "READY (test %d applied)" % n for n in (1, 2, 3, 4)}}
    lines = ["m3og m3og_v3 level %s for ILCE-7M3 4.04" % step, "euid 0x00000000 pid 0x00000001",
             "== file /proc/cmdline", "(simulated camera)", "== end 0x00000012 bytes", "== identity"]
    lines += ["lirohdr  SAME as the 4.04 file"] + ["range r%d  SAME as the 4.04 file" % k for k in range(2)]
    lines += ["page va 0x635c6000 sha256 00  differs from 4.04 (live data, not required)"]
    lines += ["page va 0x%08x sha256 00  matches 4.04" % (0x635c6000 + 0x1000 * k) for k in range(1, 16)]
    lines += ["== tv system", "slot 28 hmax 0x0000020d slot 27 hmax 0x00000001  tv system 59.94 (slot 28)"]
    lines += ["VERDICT " + name[state]]
    new = state
    if STEPS[step][2]:
        target = "stock" if step == "putback" else step
        if step != "putback" and state not in ("stock", step) and not (step == "test2" and state == "test1"):
            lines.append("NOT DONE: block fe_rec_0a byte at 0x63e0d79a holds 0xd2 (another test is applied: run the put-back first); nothing is written")
        elif target == state:
            lines.append("NOTHING TO DO: every byte already holds the target")
        else:
            lines.append("DONE: 0x00000007 bytes written in 0x00000004 runs, each read back (simulated)")
            new = target
        lines += ["after:", "VERDICT " + name[new]]
    else:
        lines += ["== mem staging va 0x64745700 phys 0x04745700 len 0x00000020", "0x64745700 " + "00" * 32, "== end",
                  "== klog phys 0x035a5000 len 0x00020000", "<6>[ 0.000000] (simulated kernel log)", "== end",
                  "== alog phys 0x03524fc0 len 0x00060040", "(simulated application log)", "== end"]
    lines.append("== done, bytes before this line: 0x00000100")
    return ("\n".join(lines) + "\n").encode(), new


def make_sim(files=None, mount_ok=True, load_status=ST_OK, write_raises=False, emulate=None):
    """The service device as the 4.04 libJiritsu behaves (M3-F011, M3-F030), with a file system and the library load."""
    import ct1_sim

    class Sim(ct1_sim.SimDriver):
        def __init__(self):
            super().__init__("senser", rules=None)
            self.fs = dict(files or {})
            self.fs.setdefault("/usr/share/pmbp/DeviceInfo.xml", b"<DeviceInfo stand-in/>")
            self.mounted = False
            self.loads = 0
            self.state = "stock"
            self.how = "canned"
            self.mount_calls = []

        def new_session(self):
            """The camera between two sessions: logged out (the stop request ends service mode), files and memory kept."""
            self._authed, self._rounds, self._challenge, self.queue, self._path = False, 0, None, [], None
            self.mounted = False

        def resolve(self, wire):
            p = wire.decode()
            if not p.startswith("/"):
                p = "/tmp/jiritsu/" + p
            parts = []
            for seg in p.split("/"):
                if seg in ("", "."):
                    continue
                if seg == "..":
                    if parts:
                        parts.pop()
                else:
                    parts.append(seg)
            return "/" + "/".join(parts)

        def _handle(self, pfunc, body):
            try:
                name = c.classify_service_packet(pfunc, body, self.rules)
            except c.GuardRefusal as exc:
                self.unexpected.append(("service packet", pfunc, body[:16].hex(), str(exc)))
                return 0xEE, b""
            payload = bytes(body[4:])
            if name == "READ_HASP":
                return 1, bytes(32)
            if name == "JIRITSU_MOUNT":
                self.mount_calls.append(payload)
                if payload == MOUNT_WORK_AREA:
                    self.mounted = mount_ok
                    return 0, struct.pack("<I", 0 if mount_ok else ST_UNMOUNTED)
                self.mounted = False
                return 0, struct.pack("<I", 0)
            if name == "SET_FILE_PATH":
                self._path = self.resolve(payload[1:])
                return 0, struct.pack("<I", 0)
            if not self.mounted:
                return 0, struct.pack("<I", ST_UNMOUNTED)
            if name == "GET_FILE2":
                if self._path not in self.fs:
                    return 0, struct.pack("<I", ST_NO_FILE)
                return 0, struct.pack("<I", 0) + self.fs[self._path]
            if name == "FILE_DELETE2":
                return 0, struct.pack("<I", 0 if self.fs.pop(self._path, None) is not None else ST_NO_FILE)
            if name == "SET_FILE2":
                data = payload[3:]
                self.fs[self._path] = data
                if write_raises:
                    raise ct1_sim.SimUsbError("cable pulled")
                if self._path == "/tmp/jiritsu/libJit.so":
                    self.loads += 1
                    if load_status != ST_OK:
                        return 0, struct.pack("<I", load_status)
                    step = next(s for s, v in STEPS.items() if v[1] == c.sha256(data))
                    if emulate:
                        res, self.state = emulate(step, data, self.state)
                        self.how = "emulated"
                    else:
                        res, self.state = canned_result(step, self.state)
                    if res is not None:
                        self.fs["/tmp_network/m3og_result.txt"] = res
                return 0, struct.pack("<I", 0)
            raise AssertionError(name)

    return Sim()


def simulate(step, sim=None, lib=None):
    """One full session against the simulated camera. Returns (session, msc driver, service driver)."""
    import ct1_sim
    c.use_pmca()
    lib = lib if lib is not None else library(step)
    session = c.Session("sim", write=False, test=TEST)
    msc = ct1_sim.SimDriver("msc")
    sim = sim or make_sim()
    sim.new_session()
    sim.rules = rules(lib)
    with contextlib.redirect_stdout(io.StringIO()):
        s2.phase_a(session, msc)
        try:
            service_session(session, sim, lambda cam: body(session, cam, step, lib), lib)
        except c.StopTest as exc:
            session.results["stopped"] = str(exc)
    return session, msc, sim


def sent(session):
    return [(e["name"], bytes.fromhex(e["hex"])[4:]) for e in session.events if e["kind"] == "service_out"]


def dry_run_lines(step):
    session, msc, sim = simulate(step, make_sim(files={"/usr/share/pmbp/DeviceInfo.xml": known_stand_in()}))
    if msc.unexpected or sim.unexpected:
        raise AssertionError("simulated camera saw something off the list: %r" % (msc.unexpected + sim.unexpected))
    lines, device, auth = [], None, 0

    def flush():
        nonlocal auth
        if auth:
            lines.append("  %d authentication packets of 516 bytes on bulk endpoint 0 (PMCA-RE SonySenserAuthDevice.authenticate)" % auth)
            auth = 0

    for e in session.events:
        if e.get("dev") and e["dev"] != device:
            flush()
            device = e["dev"]
            lines.append("To the mass-storage device (after SCSI TEST UNIT READY and INQUIRY):" if device == "msc" else "To the service device:")
        if e["kind"] == "usb_vendor_out":
            flush()
            lines.append("  vendor request out: request %d, value %s, index %s, no data  (%s)" % (e["request"], e["value"], e["index"], e["name"]))
        elif e["kind"] == "usb_out" and e["bytes"] == 516:
            auth += 1
        elif e["kind"] == "service_out":
            flush()
            b = bytes.fromhex(e["hex"])
            extra = ""
            if e["name"] == "SET_FILE_PATH":
                extra = ": " + b[5:].decode()
            elif e["name"] == "JIRITSU_MOUNT":
                extra = ": " + ("mount the work partition on /tmp/jiritsu" if b[4:] == MOUNT_WORK_AREA else "unmount it, remove /tmp/jiritsu")
            elif e["name"] == "SET_FILE2":
                extra = ": %d bytes, SHA-256 %s (%s)" % (len(b) - 7, c.sha256(b[7:]), STEPS[step][0])
            lines.append("  service packet type 0x%02x, body %s  (%s%s)" % (e["pfunc"], b[:8].hex(" ") + (" ..." if len(b) > 8 else ""), e["name"], extra))
    flush()
    return lines, session, sim


def known_stand_in():
    """The simulated camera's DeviceInfo.xml: the real 4.04 file if the analysis tree is here, else a stand-in whose
    hash is put in place of the expected one for the length of the self-test."""
    ext = Path(os.environ.get("M3_EXTRACTED", HERE.parents[4] / "a7m3_map" / "work" / "extracted" / "a7m3_404"))
    real = ext / KNOWN["from_update"]
    if real.is_file():
        return real.read_bytes()
    data = b"<DeviceInfo stand-in for the self-test/>"
    KNOWN["bytes"], KNOWN["sha256"] = len(data), c.sha256(data)
    return data


def emulator():
    """The real helper code run in Unicorn against a model camera built from the 4.04 av-cam.bin, if this machine has the
    analysis tree (a7m3_map) and unicorn; else None (the self-test then uses canned helper results)."""
    where = Path(os.environ.get("M3_EMU", HERE.parents[4] / "a7m3_map" / "camera_tests" / "K2_open_gate" / "helper"))
    if not (where / "emu_m3og.py").is_file():
        return None
    try:
        sys.path.insert(0, str(where))
        import emu_m3og as E
        if not E.AVCAM.is_file():
            return None
    except Exception:
        return None
    mem = {"m": None}

    def run(step, data, state):
        import tempfile
        cam = E.Camera()
        if mem["m"] is not None:
            cam.mem[:] = mem["m"]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "lib.so"
            p.write_bytes(data)
            r = E.Run(p, cam).go()
        if r.bad:
            raise AssertionError("emulated helper: %s" % r.bad)
        mem["m"] = bytes(cam.mem)
        res = b"".join(bytes(v) for v in cam.created.values())
        v = re.findall(rb"VERDICT READY \((stock|test [1-4] applied)\)", res)
        st = {b"stock": "stock", **{b"test %d applied" % n: "test%d" % n for n in (1, 2, 3, 4)}}.get(v[-1] if v else b"", state)
        return res, st
    return run


def selftest():
    from unittest.mock import Mock
    failures = []

    def check(name, ok, detail=""):
        print("%-78s %s%s" % (name, "pass" if ok else "FAIL", ("  " + detail) if detail and not ok else ""))
        if not ok:
            failures.append(name)

    known = known_stand_in()
    files = {"/usr/share/pmbp/DeviceInfo.xml": known}
    emu = emulator()                    # each call is a new model camera (its own memory)
    print("helper results: %s\n" % ("EMULATED (real ARM code in Unicorn, 4.04 av-cam image)" if emu else "canned (no firmware in this kit)"))

    def ends_cleanly(session, sim):
        vendor = [e["name"] for e in session.events if e["kind"] == "usb_vendor_out"]
        return (sim.mount_calls[:1] == [MOUNT_WORK_AREA] and sim.mount_calls[-1:] == [UNMOUNT_WORK_AREA] and vendor[-1:] == ["STOP_SENSER"]
                and sent(session)[-1] == ("JIRITSU_MOUNT", UNMOUNT_WORK_AREA))

    # 1. every step against a stock camera, and the ladder stock -> test1 -> test2 -> putback on one camera
    for step in STEPS:
        sim = make_sim(files=files, emulate=emulator())
        s, msc, sim = simulate(step, sim)
        k2 = s.results.get("k2", {})
        f = k2.get("result", {})
        names = [n for n, _p in sent(s)]
        check("%s: runs to the end, nothing off the list" % step, "stopped" not in s.results and not msc.unexpected and not sim.unexpected,
              str(s.results.get("stopped")))
        check("%s: one SET_FILE2 with the pinned library, loaded once, then deleted" % step,
              names.count("SET_FILE2") == 1 and sim.loads == 1 and "/tmp/jiritsu/libJit.so" not in sim.fs
              and [p for n, p in sent(s) if n == "SET_FILE2"][0][3:] == library(step))
        check("%s: result read and deleted; unmount last; stop sent" % step,
              k2.get("result_found") == RESULT_PATHS[0].decode() and "/tmp_network/m3og_result.txt" not in sim.fs and ends_cleanly(s, sim))
        want = {"dump": None, "putback": "NOTHING TO DO"}.get(step, "DONE")
        check("%s: result header ok, complete, verdict READY (stock)%s" % (step, "" if want is None else ", outcome " + want),
              f.get("header_ok") and f.get("complete") and f.get("verdicts", [""])[0] == "READY (stock)" and f.get("outcome") == want, str(f.get("verdicts")))
    sim = make_sim(files=files, emulate=emulator())
    trail = []
    for step in ("dump", "test1", "test2", "dump", "test1", "test3", "putback", "test3", "test4", "putback", "test4", "dump", "putback", "dump"):
        s, _m, sim = simulate(step, sim)
        f = s.results.get("k2", {}).get("result", {})
        trail.append((step, f.get("verdicts", [""])[-1], f.get("outcome")))
    check("ladder on one camera: test1, test2, others refused over test2, putback, test3, test4 refused over test3, putback, test4, putback",
          trail == [("dump", "READY (stock)", None), ("test1", "READY (test 1 applied)", "DONE"), ("test2", "READY (test 2 applied)", "DONE"),
                    ("dump", "READY (test 2 applied)", None), ("test1", "READY (test 2 applied)", "NOT DONE"),
                    ("test3", "READY (test 2 applied)", "NOT DONE"), ("putback", "READY (stock)", "DONE"),
                    ("test3", "READY (test 3 applied)", "DONE"), ("test4", "READY (test 3 applied)", "NOT DONE"),
                    ("putback", "READY (stock)", "DONE"), ("test4", "READY (test 4 applied)", "DONE"),
                    ("dump", "READY (test 4 applied)", None), ("putback", "READY (stock)", "DONE"), ("dump", "READY (stock)", None)], str(trail))
    s, _m, sim = simulate("dump", make_sim(files=files, emulate=emulator()))
    f = s.results.get("k2", {}).get("result", {})
    check("dump: TV system reported, kernel log and application log saved",
          f.get("tv_system") == "59.94 (slot 28)" and f.get("klog_bytes", 0) > 0 and f.get("alog_bytes", 0) > 0, str({k: f.get(k) for k in ("tv_system", "klog_bytes", "alog_bytes")}))
    # 2. the order of a session
    s, _m, sim = simulate("test1", make_sim(files=files))
    seq = sent(s)
    k = [n for n, _p in seq]
    w = k.index("SET_FILE2")
    check("order: READ_HASP, MOUNT, known answer before anything else",
          seq[0] == ("READ_HASP", b"\x00") and seq[1] == ("JIRITSU_MOUNT", MOUNT_WORK_AREA) and seq[2] == ("SET_FILE_PATH", b"\x00" + KNOWN_PATH))
    check("order: the library path is selected right before the write, deleted right after",
          seq[w - 1] == ("SET_FILE_PATH", b"\x00" + LIB_PATH) and seq[w + 1] == ("SET_FILE_PATH", b"\x00" + LIB_PATH) and k[w + 2] == "FILE_DELETE2")
    # 3. leftovers and refusals before any write
    s, _m, sim = simulate("test1", make_sim(files={**files, "/tmp/jiritsu/libJit.so": library("dump")}))
    check("own library left from an aborted run: deleted first, then the run goes on",
          "stopped" not in s.results and s.results["k2"].get("old_library_delete", {}).get("gone") and sim.loads == 1)
    s, _m, sim = simulate("test1", make_sim(files={**files, "/tmp/jiritsu/libJit.so": b"\x7fELF someone else's"}))
    check("a foreign libJit.so: stop, left alone, nothing written",
          "NOT one of this kit's" in s.results.get("stopped", "") and "SET_FILE2" not in [n for n, _ in sent(s)]
          and sim.fs.get("/tmp/jiritsu/libJit.so") == b"\x7fELF someone else's" and ends_cleanly(s, sim))
    s, _m, sim = simulate("dump", make_sim(files={**files, "/tmp_network/m3og_result.txt": b"old result"}))
    check("an earlier result: saved as old_result_0.txt and deleted, then the run goes on",
          "stopped" not in s.results and "old_result_0.txt" in s.files and s.results["k2"].get("result_found"))
    s, _m, sim = simulate("test2", make_sim(files={**files, "/tmp/jbusy": b""}))
    check("/tmp/jbusy present: stop, nothing written", "jbusy" in s.results.get("stopped", "") and sim.loads == 0 and ends_cleanly(s, sim))
    s, _m, sim = simulate("test2", make_sim(files={"/usr/share/pmbp/DeviceInfo.xml": b"<other/>"}))
    check("DeviceInfo.xml differs: stop after the known answer, nothing written",
          "DeviceInfo.xml is not the 4.04 file" in s.results.get("stopped", "") and len(sent(s)) == 5 and ends_cleanly(s, sim))
    s, _m, sim = simulate("test2", make_sim(files=files, mount_ok=False))
    check("work partition will not mount: stop at the known answer, unmount and stop still sent",
          "0x10000004" in s.results.get("stopped", "") and sim.loads == 0 and ends_cleanly(s, sim))
    # 4. failures after the write
    s, _m, sim = simulate("test1", make_sim(files=files, load_status=ST_LOAD_FAILED))
    check("library written but not loaded: deleted anyway, stops with no result",
          "no result file" in s.results.get("stopped", "") and "/tmp/jiritsu/libJit.so" not in sim.fs and ends_cleanly(s, sim))
    probe = Mock()
    probe.readHasp.return_value = b""
    answers = [bytes(4),                                                        # MOUNT
               bytes(4), bytes(4) + known,                                      # known answer
               bytes(4), struct.pack("<I", ST_NO_FILE),                         # library absent
               bytes(4), struct.pack("<I", ST_NO_FILE), bytes(4), struct.pack("<I", ST_NO_FILE),   # no results
               bytes(4), struct.pack("<I", ST_NO_FILE),                         # not busy
               bytes(4), OSError("cable pulled"),                               # select, then the write fails
               bytes(4), bytes(4), bytes(4), struct.pack("<I", ST_NO_FILE),     # delete + confirm
               bytes(4)]                                                        # unmount
    probe._sendAdjustControlPacket.side_effect = answers
    session = c.Session("sim", write=False, test=TEST)
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            body(session, probe, "test1", library("test1"))
        except c.StopTest as exc:
            session.results["stopped"] = str(exc)
    calls = probe._sendAdjustControlPacket.call_args_list
    check("the write gets no answer: the library is still deleted, then unmount",
          "no answer" in session.results.get("stopped", "") and calls[-1].args == (0x1001, MOUNT, UNMOUNT_WORK_AREA)
          and any(cl.args[1] == FILE_DELETE2 for cl in calls))
    # 5. the guard
    lib = library("test1")
    g_rules = rules(lib)
    adj = lambda code, payload, cat=0x1001: struct.pack("<HH", cat, code) + payload   # noqa: E731
    for label, pfunc, data in (
            ("SET_FILE2 of other bytes", c.PFUNC_ADJUST, adj(SET_FILE2, b"\x00\xff\x00" + lib[:-1] + bytes([lib[-1] ^ 1]))),
            ("SET_FILE2 of another kit's pinned library", c.PFUNC_ADJUST, adj(SET_FILE2, b"\x00\xff\x00" + library("test2"))),
            ("format (0x4003)", c.PFUNC_ADJUST, adj(0x4003, b"\x00")),
            ("MOUNT of the memory card (area 1)", c.PFUNC_ADJUST, adj(MOUNT, b"\x01\x00")),
            ("Jiritsu MODE (0x4001)", c.PFUNC_ADJUST, adj(0x4001, b"\x00")),
            ("Jiritsu START (0x4004)", c.PFUNC_ADJUST, adj(0x4004, b"\x00")),
            ("Jiritsu FIRMUP (0x4006)", c.PFUNC_ADJUST, adj(0x4006, b"\x00")),
            ("old SET_FILE (0x4007)", c.PFUNC_ADJUST, adj(0x4007, b"\x00")),
            ("backup read (0x603/5)", c.PFUNC_ADJUST, adj(0x0005, b"\x01", 0x0603)),
            ("SET_FILE_PATH to an unlisted path", c.PFUNC_ADJUST, adj(SET_FILE_PATH, b"\x00../../etc/passwd")),
            ("memory dump packet type 0xff03", 0xFF03, struct.pack("<HH", 0, 0) + b"\x00")):
        try:
            c.classify_service_packet(pfunc, data, g_rules)
            check("guard refuses %s" % label, False, "was allowed")
        except c.GuardRefusal:
            check("guard refuses %s" % label, True)

    def stateful(fn):
        sim = make_sim(files=files)
        sim.rules = g_rules
        session = c.Session("sim", write=False, test=TEST)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                service_session(session, sim, lambda cam: (command(cam, MOUNT, MOUNT_WORK_AREA), fn(cam)), lib)
        except c.GuardRefusal as exc:
            return str(exc), sim
        return None, sim
    why, sim = stateful(lambda cam: (select(cam, RESULT_PATHS[0]), command(cam, SET_FILE2, b"\x00\xff\x00" + lib)))
    check("guard refuses SET_FILE2 onto a result path", why and "SET_FILE2 when" in why and sim.loads == 0)
    why, sim = stateful(lambda cam: (select(cam, LIB_PATH), command(cam, SET_FILE2, b"\x00\xff\x00" + lib),
                                     select(cam, LIB_PATH), command(cam, SET_FILE2, b"\x00\xff\x00" + lib)))
    check("guard refuses a second SET_FILE2 in one session", why and "second file write" in why and sim.loads == 1)
    why, sim = stateful(lambda cam: (select(cam, KNOWN_PATH), command(cam, FILE_DELETE2, b"\x00\xff")))
    check("guard refuses FILE_DELETE2 of DeviceInfo.xml", why and "FILE_DELETE2 when" in why and "/usr/share/pmbp/DeviceInfo.xml" in sim.fs)
    # 6. pins
    check("every step's library is the pinned build and fits one packet", all(len(library(s)) <= LIB_MAX for s in STEPS))
    # 7. dry run
    lines, _s, _sim = dry_run_lines("test2")
    txt = "\n".join(lines)
    check("dry run (test2) shows the mount, the write of libJit_m3og_test2.so, the deletes and the unmount",
          txt.count("JIRITSU_MOUNT") == 2 and "SET_FILE2: " in txt and STEPS["test2"][0] in txt and txt.count("FILE_DELETE2") == 2
          and txt.index("mount the work partition") < txt.index("SET_FILE2") < txt.index("unmount it"))
    print("\n%d failed" % len(failures))
    return not failures


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", nargs="?", choices=sorted(STEPS))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--selftest", action="store_true")
    mode.add_argument("--list", action="store_true")
    mode.add_argument("--go", action="store_true")
    parser.add_argument("--firmware-shown", help="the version the camera's menu shows (must be 4.04)")
    parser.add_argument("--yes", action="store_true", help="do not ask before a step that writes")
    args = parser.parse_args()

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
              % (len(msc), ["%04x:%04x" % (d.idVendor, d.idProduct) for d in msc], len(senser), ["%04x:%04x" % (d.idVendor, d.idProduct) for d in senser]))
        print("Nothing was sent to any device.")
        return
    if not args.step:
        parser.error("name the step: dump, test1, test2, test3, test4 or putback")
    lib = library(args.step)
    if args.dry_run:
        lines, _s, _sim = dry_run_lines(args.step)
        print("Kit 2, step %s (%s), would send in this order (simulated camera):" % (args.step, STEPS[args.step][3]))
        print("\n".join(lines))
        return
    if (args.firmware_shown or "").strip() != EXPECTED_FIRMWARE:
        raise SystemExit("This kit is for an %s on firmware %s only. Pass --firmware-shown with the version the camera's menu shows "
                         "(MENU > Setup > Version)." % (EXPECTED_MODEL, EXPECTED_FIRMWARE))
    if STEPS[args.step][2] and not args.yes:
        print("Step %s: %s" % (args.step, STEPS[args.step][3]))
        print("It changes the camera's working memory (RAM) until a restart, a battery pull or the put-back step. Nothing is flashed.")
        if input("Type YES to go on: ").strip() != "YES":
            raise SystemExit("Not confirmed. Nothing was sent.")
    with c.Session(args.step, test=TEST) as session:
        session.results.update(kit=KIT, step=args.step, firmware_shown_on_camera=args.firmware_shown)
        inner = s2.connect(session)
        model = (session.results.get("msc_inquiry") or {}).get("model")
        if model is not None:
            session.say("Mass-storage INQUIRY model text: %r" % model)
        try:
            service_session(session, inner, lambda cam: body(session, cam, args.step, lib), lib)
        finally:
            import time
            time.sleep(3)
            c.print_pnp(session, "after the stop request")


if __name__ == "__main__":
    main()
