"""A7 III (ILCE-7M3, firmware 4.04) kit 2 (m3kit2_v13): open-gate tests, and a debug dump.

v13 (2026-11-27), after the v12 run (a7m3_map FINDINGS M3-F060): with the memory ports at 3529 lines the faults the log
showed for every frame are gone, and a new one appears. The first frame passes every stage; in the second the front
end's image generator does not start, its link generator stands at line 156, and the output keeps sending the stored
frame: the picture stands still. 156 = 64 (the link line where the image stage starts) + 92 (the rows added), which
reads as the image stage ending the first frame 92 lines short. The front end's drive table is the one front-end table
tests 12 and 13 left at the stock height (crops of 3392 lines, an output size of 3437). v13 adds test14 = test 12 plus
that table's twelve heights raised by 92 (the words of test 10), and test15 = test 12 plus ten of them (the two
inner-window heights stay stock).

v12 (2026-11-27), after the v11 run (a7m3_map FINDINGS M3-F058): test 11 recorded the same frame as test 9, so the line
period was not the cause; the time budget is withdrawn. The dump's copy of the camera's own log worked, and the log
names the cause. With a test applied the firmware logs, every frame, "Ofmt_Mwrap::Deactivate() status wait failed",
"Lost CAMOUT_V .. sgc2[hq:0x05f7 vq:0x0d6a]" and "S-Ele Refresh"; its status print shows the front end's output-format
generator resting at line 3437. That is the line count of the front end's three frame-memory port entries (two write
ports, one read port), which tests 9 to 11 left stock. v12 adds test12 = test 11 plus those three entries at 3529
lines, and test13 = test 9 plus the same (the stock line period).

v11 (2026-11-27), after the v10 run (a7m3_map FINDINGS M3-F056): test 9 removed the black bar and the strip, so the
front end's stock frame was their cause. Its frame then ran out of time: the transfer sends one line every 11.6 us and
starts 1.64 ms after the frame start, so 3451 lines fit before the next frame; 3453 arrived and test 9 asked for 3518.
The last 40 rows of the recorded frame were never written. v11 adds test11 = test 9 with the line period shortened
from 836 to 814, so the taller frame ends when the stock one does. Test 10 made things worse and is no longer on the
tester page. The dump's copy of the camera's own log failed in v10 on a header word that changes while the camera
runs; the check is corrected. The copy of the kernel's application log (always empty) is dropped.

v10 (2026-11-27), after the v9 run and a trace of the picture path (a7m3_map FINDINGS M3-F050..F054, PIPELINE.md): tests
7 and 8 recorded test 3's frame again. The trace found a stage no test had written: the front end between the sensor
and the camera core is programmed from its own per-mode register lists, and they still describe the stock frame (3436
lines). v10 adds test9 (test 3 plus those lists: 45 register fields), test10 (test 9 plus the front end's geometry
table), and dfelog (one flag byte: the firmware's own status print for the front end). The dump now copies the camera
core's own log lines out of RAM, which is where that print goes. Tests 9 and 10 set the no-restart bit and the
status print themselves.

v9 (2026-11-27), after the v8 run (a7m3_map FINDINGS M3-F049): test 6 (first row 281) recorded test 3's frame again, so
the first row does not matter. Tests 3 to 6 all deliver the stock head lines plus half the added rows, which equals
(our line-pair count + the stock one) - 10 lines: one new count plus one stock count. The sensor's row-count register
and the timing pair's count were always raised by the same amount, so v9 adds two steps that double one of them:
test7 (pair 815 / 1810) and test8 (3596 sensor rows). Whichever gives a whole frame names the second copy.

v8 (2026-11-27), after the v7 run (a7m3_map FINDINGS M3-F048): test 5 (test 3 + size row) recorded the same frame as
test 3 (picture to row 2136, black to 2155, four strip rows), so the size row does not set the last row. In tests 3,
4 and 5 the valid picture ends at the stock last sensor row: only the rows gained by starting higher arrive. v8 adds
test6 = test 3 with the first row moved up by the whole 92 rows (281 instead of 327), so every row it needs lies above
the stock last row.

v7 (2026-11-27), after the v6 run and two camera clips (a7m3_map FINDINGS M3-F046, M3-F047): test 3 (line count only)
still stutters, so the shortened line period is cleared. In the clips the picture is valid for the stock crop plus
HALF the added rows, then black, then the top of the frame again: the valid data ends at the stock last sensor row.
The register list holds no other window register, so that row is set from something the design left stock. v7 adds
test5 = test3 plus the size row's inner height (ROM row, runtime entry, the two read-out words the firmware derives).

v6 (2026-11-27), after the v5 timing read (a7m3_map FINDINGS M3-F044): the output sync sits 22.49 / 22.50 / 22.54 ms
after the frame start in stock, test 4 and test 2, so it does not follow the picture height. With a test applied the
sequence's two frame counters are one apart, the refresh loop runs about nine times a second, and test 2 showed the
top strip of the picture at the bottom. Tests 2 and 4 change the line count and the line period together. v6
redefines test3 as the step that changes only the line count: +92 rows, V2 1764, line period stock (836) on the
59.94 system. (The 50 system has no room: its stock pair already leaves the minimum blank.)

v5 (2026-11-27), after the v4 run (a7m3_map FINDINGS M3-F043): with the forced restart switched off the camera stays
on and stutters; with the refresh loop off the picture is jittery and dark; the loop's lost-output-sync path did run.
The imaging pipeline stops when USB starts, so a dump holds the time stamps of the last frame before USB. v5 changes
only the dump (it also copies the imaging sequence's state objects) and reports that last frame's timing; the tester
page now takes the dumps with the dial left on movie.

v4 (2026-11-27), after a second tester's run of v3 on a 50-system camera (a7m3_map FINDINGS M3-F042): tests 2, 3 and 4
each showed the open-gate picture for about a second, then the camera restarted itself at the same place as before.
So the picture path works with the matched timing pair, at every height, and the firmware's output-sync refresh loop
still gives up after ten retries. v4 adds the firmware's own two switches for that loop as steps (norestart, nocheck),
and the dump reads the loop's counters and time stamps, so a run with a switch set shows what the loop was doing.

v3 (2026-11-26), after the second run on a tester's camera (a7m3_map FINDINGS M3-F039..F041): v2's test 1 ran with no
fault; v2's test 2 restarted the camera when movie mode started. The restart was the firmware's own forced stop
("S-Ele Refresh ng force exception") after ten refreshes of a lost output sync, and it put the 4.04 bytes back by
itself. Cause as far as the firmware shows it: test 2 made the front-end records 624 lines taller but left the
camera-core timing pair of that drive at the stock 3436 lines. v3 moves the timing pair with the records, adds two
smaller heights, and the dump now also copies the camera's application log.

Twenty steps, each one service session that loads one small helper library on the camera (helper/m3og.c, design og_m3_v2
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
  test3     v6: the line count alone. 3504 rows, picture 3468 rows (stretch 1.027), timing pair 836 / 1764: the stock
            line period on the 59.94 system (801 on the 50 system, which has no room for more lines at 823).
  test4     The same for a quarter: 3568 rows, picture 3532 rows (stretch 1.046), line rate 2 % (5 %) above stock.
  test5     v7: test 3's bytes plus the size row's inner height (3376 -> 3468) in the ROM row, the runtime entry
            and the two read-out time words: tests whether the size row is what ends the picture early.
  test6     v8: test 3's bytes with the first sensor row at 281 instead of 327 (one byte differs from test 3): tests
            whether the valid picture ends at a fixed sensor row.
  test7     v9: test 3's bytes with the timing pair 815 / 1810 (781 / 1810 on the 50 system) instead of 836 / 1764.
  test8     v9: test 3's bytes with the sensor's row-count register at 1798 (3596 rows) instead of 1752.
  test9     v10: test 3's bytes plus the front end's register lists of the 4K full-frame mode: every line count + 92
            (receiver, link, image, output format, transfer generator, both channels), the two frame totals, and
            the transfer cycle. Also sets the no-restart bit and the status print (norestart and dfelog below).
  test10    v10: test 9's bytes plus the front end's drive table (twelve height words + 92). Withdrawn after its run:
            a brightness step between the two halves of the picture.
  test11    v11: test 9's bytes with the line period of the timing pair and of the front end's transfer generator at
            814 instead of 836 (59.94 system). On the 50 system test 9 already holds that value (801): same bytes.
  test12    v12: test 11's bytes plus the front end's three frame-memory port entries (two write ports, one read
            port) at 3529 lines instead of 3437. The memory behind them holds 4139 lines.
  test13    v12: test 9's bytes plus the same three entries. On the 50 system the same bytes as test 12.
  test14    v13: test 12's bytes plus the twelve height words of the front end's drive table raised by 92 (the
            words of test 10, which still had the stock ports).
  test15    v13: test 12's bytes plus ten of those words: the two inner-window heights (3376) stay stock.
  putback   WRITES the 4.04 bytes back wherever a test changed them, and clears the switches below. A restart or a
            battery pull does the same.
  norestart WRITES one bit (0x40 of the refresh loop's switch byte): the loop keeps retrying but never forces the
            restart. Run it after a test step; the next dump shows how often the loop retried.
  nocheck   WRITES one bit (0x02 of the same byte): the refresh loop does nothing. Shows whether the picture is good
            when the loop leaves it alone.
  dfelog    v10: WRITES four bits of one flag byte: the firmware's own status print for its front end then writes
            the generators' cycles, counters and states to the camera's log whenever the sensor's drive mode
            changes. The next dump copies that log.

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
klog.txt, camlog_first.txt, camlog_last.txt and one .bin per memory range).
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

KIT = "m3kit2_v13"
TEST = "M3K2"
EXPECTED_MODEL = "ILCE-7M3"
EXPECTED_FIRMWARE = "4.04"
HELPER = HERE / "helper"
c.PREDICTIONS = HERE / "predictions.json"
KNOWN = json.loads((HERE.parent / "K1_readonly" / "expected_404.json").read_text(encoding="utf-8"))["files"]["/usr/share/pmbp/DeviceInfo.xml"]

# step -> (library, SHA-256, writes?, what it does)
STEPS = {
    "dump": ("libJit_m3og_dump.so", "c848f4932a9738c73741f12a7d5f4133dc499e488af3cf1df37b1b89219ecc01", False,
             "read-only dump: facts, logs, where av-cam is, what the design's bytes hold, the tables, the refresh loop's state"),
    "test1": ("libJit_m3og_test1.so", "70cb1011ddfb6524f14e08314117bc207bceb0a514f4e022dcfff9fb5e63f229", True,
              "TEST 1: the 4K 24p/25p full-frame sensor mode reads the whole sensor height (7 bytes)"),
    "test2": ("libJit_m3og_test2.so", "64c19aac94fba024d9bcc1565278f7ddd70ecc7e91d476892d86298ac1626d99", True,
              "TEST 2: sensor + front end + timing: the whole 3:2 height squeezed into the stock 4K file"),
    "test3": ("libJit_m3og_test3.so", "afd28da09a0b8147c485c41f2e47af18e7d0bc543301568f02a3bc0d1e08ae86", True,
              "TEST 3: 92 more rows with the stock line period (picture 3468 rows; 59.94 system)"),
    "test4": ("libJit_m3og_test4.so", "47d4896be04ee259e4a29e3981aed50b4e781db8f0cbb01ad68af5c430514122", True,
              "TEST 4: as test 2 for a quarter of the extra height (picture 3532 rows)"),
    "test5": ("libJit_m3og_test5.so", "459fb167e781b6dabe0a25f24b65727cb9dee33a61a4d673702a6ff9a1b169ab", True,
              "TEST 5: test 3 plus the size row (inner height 3468): does the whole taller picture arrive?"),
    "test6": ("libJit_m3og_test6.so", "bb809fc50e9bc52b854756092a69159a502cb56f81983fa74095cba39ddfec36", True,
              "TEST 6: test 3 with the first sensor row moved up by all 92 rows (row 281): is the frame whole?"),
    "test7": ("libJit_m3og_test7.so", "62e4141ccf52bb12929fa80df1aae587e2a39cca6168f814c3add5231f0f3480", True,
              "TEST 7: test 3 with the timing pair's line count raised twice as far (1810): is the frame whole?"),
    "test8": ("libJit_m3og_test8.so", "d8cf12bb20454d7bcaaccf4a552a58d98ca1c3bc24076e96db36913115fb4b2f", True,
              "TEST 8: test 3 with the sensor's row count raised twice as far (3596 rows): is the frame whole?"),
    "test9": ("libJit_m3og_test9.so", "76fab380b597efcc5a90b9d5fb33a7bd59d079a992063a2531ce65045fa4861f", True,
              "TEST 9: test 3 plus the front end's own line counts (45 fields); also sets no-restart and the front-end log"),
    "test10": ("libJit_m3og_test10.so", "d864cd98a882cfa70351ab668c6510c4e58c436b0fa0f8f60afacdbb7eac9e0a", True,
               "TEST 10: test 9 plus the front end's geometry table (12 height words); also sets no-restart and the front-end log"),
    "test11": ("libJit_m3og_test11.so", "e10bdf75d64c7dacf7081b3260195210f748a52f47e9f6b0580136b23543986e", True,
               "TEST 11: test 9 with the line period 814 so the taller frame ends in time; also sets no-restart and the front-end log"),
    "test12": ("libJit_m3og_test12.so", "8c29ae776d527a380e4668ae1d91af0bbad0f54cc32f2f2b2efae98cb2f1c76a", True,
               "TEST 12: test 11 plus the front end's three frame-memory ports at 3529 lines; also sets no-restart and the front-end log"),
    "test13": ("libJit_m3og_test13.so", "e412cc9904a2139a803d652639e374ae0755ff4b26323036026f99b34572c834", True,
               "TEST 13: test 9 plus the same three ports (stock line period); also sets no-restart and the front-end log"),
    "test14": ("libJit_m3og_test14.so", "f9cf675a9fbb1aaa716e9aca067de1348b1e69af7b56d6a28e8f3856fea277ee", True,
               "TEST 14: test 12 plus the front end's geometry table at the taller height (12 height words); also sets no-restart and the front-end log"),
    "test15": ("libJit_m3og_test15.so", "a977b7fa91db46eb4967270ecc32ea6a25c76785bf2f80e4e7a596bb24879a59", True,
               "TEST 15: test 12 plus ten of those height words (the two inner heights stay stock); also sets no-restart and the front-end log"),
    "putback": ("libJit_m3og_putback.so", "deec64a752c7304715039470e0591c69f99d99d41ed23da82ee0e7fea04dc52b", True,
                "PUT BACK: the 4.04 bytes again wherever a test changed them; the switches and the front-end log cleared"),
    "norestart": ("libJit_m3og_norestart.so", "a2b3b3aa3e5a44cea4ce0f5943e22e2e769550c64287f6a5395dd3af4566e3cc", True,
                  "NO RESTART: the camera's refresh loop keeps retrying but never forces a restart (1 bit)"),
    "nocheck": ("libJit_m3og_nocheck.so", "da5c485e77735bd25b1951679bd8718766f03001e026d2be5973accf81cdf0b4", True,
                "NO CHECK: the camera's refresh loop is switched off (1 bit)"),
    "dfelog": ("libJit_m3og_dfelog.so", "50d7dce30393e34aa536b3e36ef0fc4e0ec5baa617f38a0251cd711488593ee5", True,
               "FRONT-END LOG: the firmware's own status print for its front end is switched on (4 bits of one byte)"),
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
    for key, name in (("_klog", "klog.txt"), ("_alog", "alog.txt"), ("_camlog_first", "camlog_first.txt"), ("_camlog_last", "camlog_last.txt")):
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
        m = re.match(r"block (\S+) va (0x[0-9a-f]+) len (0x[0-9a-f]+) .*  (STOCK|TEST\d+|MIXED|OTHER)$", ln)
        if m:
            blocks.setdefault(m.group(1), []).append(m.group(4))
    facts = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "header": lines[0] if lines else "",
             "header_ok": bool(lines) and lines[0].startswith("m3og ") and ("level %s for ILCE-7M3 4.04" % step) in lines[0],
             "complete": any(ln.startswith("== done") for ln in lines[-3:]),
             "identity_same": sum(1 for ln in lines if ln.endswith("SAME as the 4.04 file")),
             "image_pages_live": [ln.split()[2] for ln in lines if ln.startswith("page va ") and "differs from 4.04" in ln],
             "identity_differs": sum(1 for ln in lines if ln.endswith("DIFFERS from the 4.04 file")),
             "guard": [ln[6:] for ln in lines if ln.startswith("GUARD ")],
             "dfelog": [ln[7:] for ln in lines if ln.startswith("DFELOG ")],
             "camlog": [ln for ln in lines if ln.startswith("camlog ")],
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
    facts["last_frame"] = last_frame(ranges)
    for key in ("klog", "alog", "camlog_first", "camlog_last"):
        k = re.search(r"== %s phys \S+ len \S+\n(.*?)\n== (end|cut)" % key, t, re.S)
        if k:
            facts["_" + key] = k.group(1).encode("utf8", "replace")
            facts[key + "_bytes"] = len(facts["_" + key])
    facts["log_lines"] = log_highlights(facts.get("_camlog_first", b"") + b"\n" + facts.get("_camlog_last", b""))
    return facts


def log_highlights(blob):
    """The lines of the camera core's log that say what the front end runs and why a frame was refreshed (first of each)."""
    t = blob.decode("utf8", "replace")
    out = []
    for pat in (r"\[DrvSgc0Start\][^.\n]{0,70}", r"HVcyc:[ 0-9a-fDT]{0,60}", r"Lost CAMOUT_V[^\n]{0,90}?\]", r"S-Ele Refresh[^.\n]{0,40}",
                r"Ofmt_Mwrap::Deactivate\(\) status wait failed", r"DfeCamAif\d+ memSize\d+<rawSize\d+[^.\n]{0,30}", r"camIntHandler1: fact=[0-9a-f]+"):
        found = re.findall(pat, t)
        for m in list(dict.fromkeys(found))[:3]:
            out.append(m.strip())
    flat = t.replace("\r", "").replace("\n", "")
    for m in list(dict.fromkeys(re.findall(r"(?:imgSGC|nrSGC|OfSGC|OutSGC|ZpdPreSGC|(?:Lnk|Rcv|Trs|Drv)SGC(?: sub)?\d):Last frame is not started", flat)))[:6]:
        out.append(m)
    for a, b in list(dict.fromkeys(re.findall(r",L([0-9a-f]{8} [0-9a-f]{8}) [0-9a-f]{8} [0-9a-f]{8},I([0-9a-f]{8} [0-9a-f]{8}),N", flat)))[:4]:
        if a.split()[1] != "00000000":                 # channel 1 in use: a 4K status print
            out.append("link L%s image I%s" % (a, b))
    return out


def last_frame(ranges):
    """The timing of the last frame before USB stopped the imaging pipeline, from the dump's memory ranges (the firmware's
    own time stamps, in half microseconds): how long after the sensor frame start (CamV) the output sync (CamOutV) came.
    The CamV stamp keeps ticking on its grid while USB is on, so the phase is taken modulo the frame time."""
    try:
        def cell(prefix, va):
            name = next(k for k in ranges if k.startswith(prefix + "_0x"))
            base = int(name.rsplit("_0x", 1)[1], 16)
            return struct.unpack_from("<I", ranges[name], va - base)[0]
        h, v = cell("sgc1_param", 0x64326DC4 + 0x38), cell("sgc1_param", 0x64326DC4 + 0x3C)
        clocks = 1440000 if (h, v) == (525, 2740) else h * v            # the 50-system 4K row has a fractional part
        frame = clocks / 36.0 * 2                                       # in half microseconds
        camv, camout = cell("sync_stamps", 0x6435643C), cell("sync_stamps", 0x64356064)
        phase = (-((camv - camout) % 0x100000000)) % frame
        return {"sgc1_h": h, "sgc1_v": v, "frame_ms": round(frame / 2000.0, 4), "camoutv_after_camv_ms": round(phase / 2000.0, 3),
                "camoutv_stamp": camout, "eestart_before_camoutv_ms": round(((camout - cell("sync_stamps", 0x64356440)) % 0x100000000) / 2000.0, 3),
                "idtdriver_before_camoutv_ms": round(((camout - cell("sync_stamps", 0x64356438)) % 0x100000000) / 2000.0, 3),
                "refresh_counter": cell("refresh_state", 0x643548DC), "kick_frame": cell("refresh_state", 0x64354794),
                "camoutv_frame": cell("refresh_state", 0x643547C8), "lost_sync_seen": cell("refresh_latch", 0x64688AA8) >> 8 & 0xFF}
    except Exception:                                                   # an older or cut dump: no figures
        return None


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
    if f.get("guard"):
        session.say("  Refresh-loop switch: " + f["guard"][-1])
    if f.get("dfelog"):
        session.say("  Front-end log switch: " + f["dfelog"][-1])
    if f.get("camlog"):
        session.say("  Camera log: first lines %d bytes, last lines %d bytes%s" % (f.get("camlog_first_bytes", 0), f.get("camlog_last_bytes", 0),
                    "" if all("NOT" not in ln for ln in f["camlog"]) else " (an area was not where expected: see m3og_result.txt)"))
        for ln in f.get("log_lines") or []:
            session.say("    log: " + ln)
    lf = f.get("last_frame")
    if lf:
        session.say("  Last frame before USB: frame %.3f ms (cycle %d x %d), output sync %.3f ms after frame start, refresh count %d, lost sync seen: %s"
                    % (lf["frame_ms"], lf["sgc1_h"], lf["sgc1_v"], lf["camoutv_after_camv_ms"], lf["refresh_counter"], "yes" if lf["lost_sync_seen"] else "no"))
    if f["outcome"]:
        session.say("  Outcome: %s  (%s)" % (f["outcome"], f["outcome_line"]))
    for p in f["problems"]:
        session.say("  " + p)


# ------------------------------------------------------------ simulated camera

def canned_result(step, state):
    """What the helper would report on a model camera when it cannot be emulated here (the kit ships no firmware).
    state: the design's state before the step ('stock', 'test1' .. 'test15'), with '|<hex>' appended while a switch bit is
    set (0x40 / 0x02 = the refresh loop's bits, 0x100 = the front-end log). Returns (text, new state)."""
    name = {"stock": "READY (stock)", **{"test%d" % n: "READY (test %d applied)" % n for n in range(1, 16)}}
    state, _bar, gtxt = state.partition("|")
    guard = int(gtxt or "0", 16)
    gline = lambda g: ("GUARD flag byte 0x%02x  refresh loop %s\nDFELOG flag byte 0x%02x  front-end status print %s"   # noqa: E731
                       % (g & 0xFF, "OFF" if g & 2 else "on, NO FORCED RESTART" if g & 0x40 else "STOCK", 0x0F if g & 0x100 else 0, "ON" if g & 0x100 else "off"))
    lines = ["m3og m3og_v3 level %s for ILCE-7M3 4.04" % step, "euid 0x00000000 pid 0x00000001",
             "== file /proc/cmdline", "(simulated camera)", "== end 0x00000012 bytes", "== identity"]
    lines += ["lirohdr  SAME as the 4.04 file"] + ["range r%d  SAME as the 4.04 file" % k for k in range(2)]
    lines += ["page va 0x635c6000 sha256 00  differs from 4.04 (live data, not required)"]
    lines += ["page va 0x%08x sha256 00  matches 4.04" % (0x635c6000 + 0x1000 * k) for k in range(1, 16)]
    lines += ["== tv system", "slot 28 hmax 0x0000020d slot 27 hmax 0x00000001  tv system 59.94 (slot 28)"]
    lines += ["VERDICT " + name[state], gline(guard)]
    new = state
    if step in ("norestart", "nocheck", "dfelog"):
        bit = {"norestart": 0x40, "nocheck": 0x02, "dfelog": 0x100}[step]
        lines.append("NOTHING TO DO: the switch bit is already set" if guard & bit
                     else "DONE: 0x00000001 bytes written in 0x00000001 runs, each read back (simulated)")
        guard |= bit
        lines += ["after:", "VERDICT " + name[new], gline(guard)]
    elif STEPS[step][2]:
        target = "stock" if step == "putback" else step
        cleared = step == "putback" and guard
        if cleared:
            lines.append("guard: switch bits cleared, 1 byte written and read back")
            guard = 0
        sets = 0x140 if step in ("test9", "test10", "test11", "test12", "test13", "test14", "test15") else 0
        if step != "putback" and state not in ("stock", step) and (step, state) not in (("test2", "test1"), ("test5", "test3"), ("test9", "test3"),
                                                                                    ("test10", "test9"), ("test10", "test3"), ("test11", "test9"), ("test11", "test3"), ("test12", "test11"), ("test12", "test9"),
                                                                                    ("test12", "test3"), ("test12", "test13"), ("test13", "test9"), ("test13", "test3"),
                                                                                    ("test14", "test12"), ("test14", "test11"), ("test14", "test9"), ("test14", "test3"), ("test14", "test13"),
                                                                                    ("test14", "test10"), ("test14", "test15"), ("test15", "test12"), ("test15", "test11"), ("test15", "test9"),
                                                                                    ("test15", "test3"), ("test15", "test13")):
            lines.append("NOT DONE: block fe_rec_0a byte at 0x63e0d79a holds 0xd2 (another test is applied: run the put-back first); nothing is written")
        elif target == state and not cleared and (guard & sets) == sets:
            lines.append("NOTHING TO DO: every byte already holds the target")
        else:
            lines.append("DONE: 0x00000007 bytes written in 0x00000004 runs, each read back (simulated)")
            new = target
            guard |= sets
        lines += ["after:", "VERDICT " + name[new], gline(guard)]
    else:
        lines += ["== mem staging va 0x64745700 phys 0x04745700 len 0x00000020", "0x64745700 " + "00" * 32, "== end",
                  "== klog phys 0x035a5000 len 0x00020000", "<6>[ 0.000000] (simulated kernel log)", "== end",
                  "== camlog", "camlog subsystem phys 0x03162054 header 00  as expected",
                  "camlog area camlog_first phys 0x031c412c size 0x0000a044 header 00  as expected, written up to 0x00000a86",
                  "== camlog_first phys 0x031c4150 len 0x0000a020", "[DrvSgc0Start]mode4,syncMode0,H525,V2860,VdNum1 .HVcyc: D0 20c0b2c T0 3430d6c T1        0 T2        0", "== end",
                  "camlog area camlog_last phys 0x031a20e4 size 0x00002024 header 00  as expected, written up to 0x00000a86",
                  "== camlog_last phys 0x031a2108 len 0x00002000", "(simulated camera log)", "== end"]
    lines.append("== done, bytes before this line: 0x00000100")
    return ("\n".join(lines) + "\n").encode(), new + ("|%x" % guard if guard else "")


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
        v = re.findall(rb"VERDICT READY \((stock|test \d+ applied)\)", res)
        st = state if not v else "stock" if v[-1] == b"stock" else "test" + v[-1].split()[1].decode()
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
    sim = make_sim(files=files, emulate=emulator())
    trail = []
    for step in ("test4", "norestart", "dump", "nocheck", "dump", "putback", "dump"):
        s, _m, sim = simulate(step, sim)
        f = s.results.get("k2", {}).get("result", {})
        trail.append((step, f.get("verdicts", [""])[-1], f.get("outcome"), (f.get("guard") or [""])[-1].split("refresh loop ")[-1]))
    check("switch ladder: test4, norestart, nocheck leave the test applied; putback clears the test and both switches",
          trail == [("test4", "READY (test 4 applied)", "DONE", "STOCK"), ("norestart", "READY (test 4 applied)", "DONE", "on, NO FORCED RESTART"),
                    ("dump", "READY (test 4 applied)", None, "on, NO FORCED RESTART"), ("nocheck", "READY (test 4 applied)", "DONE", "OFF"),
                    ("dump", "READY (test 4 applied)", None, "OFF"), ("putback", "READY (stock)", "DONE", "STOCK"),
                    ("dump", "READY (stock)", None, "STOCK")], str(trail))
    sim = make_sim(files=files, emulate=emulator())
    trail = []
    for step in ("test3", "test9", "test10", "dump", "test9", "putback", "dfelog", "dump", "putback", "dump"):
        s, _m, sim = simulate(step, sim)
        f = s.results.get("k2", {}).get("result", {})
        trail.append((step, f.get("verdicts", [""])[-1], f.get("outcome"), (f.get("guard") or [""])[-1].split("refresh loop ")[-1],
                      (f.get("dfelog") or [""])[-1].split("status print ")[-1]))
    check("v10 ladder: test9 over test3 and test10 over test9 go through and set both switches; test9 over test10 is refused; putback clears all",
          trail == [("test3", "READY (test 3 applied)", "DONE", "STOCK", "off"), ("test9", "READY (test 9 applied)", "DONE", "on, NO FORCED RESTART", "ON"),
                    ("test10", "READY (test 10 applied)", "DONE", "on, NO FORCED RESTART", "ON"), ("dump", "READY (test 10 applied)", None, "on, NO FORCED RESTART", "ON"),
                    ("test9", "READY (test 10 applied)", "NOT DONE", "on, NO FORCED RESTART", "ON"), ("putback", "READY (stock)", "DONE", "STOCK", "off"),
                    ("dfelog", "READY (stock)", "DONE", "STOCK", "ON"), ("dump", "READY (stock)", None, "STOCK", "ON"),
                    ("putback", "READY (stock)", "DONE", "STOCK", "off"), ("dump", "READY (stock)", None, "STOCK", "off")], str(trail))
    sim = make_sim(files=files, emulate=emulator())
    trail = []
    for step in ("test9", "test11", "dump", "test9", "putback", "test3", "test11", "putback", "dump"):
        s, _m, sim = simulate(step, sim)
        f = s.results.get("k2", {}).get("result", {})
        trail.append((step, f.get("verdicts", [""])[-1], f.get("outcome"), (f.get("guard") or [""])[-1].split("refresh loop ")[-1]))
    check("v11 ladder: test11 goes over test9 and over test3; test9 over test11 is refused; putback clears all",
          trail == [("test9", "READY (test 9 applied)", "DONE", "on, NO FORCED RESTART"), ("test11", "READY (test 11 applied)", "DONE", "on, NO FORCED RESTART"),
                    ("dump", "READY (test 11 applied)", None, "on, NO FORCED RESTART"), ("test9", "READY (test 11 applied)", "NOT DONE", "on, NO FORCED RESTART"),
                    ("putback", "READY (stock)", "DONE", "STOCK"), ("test3", "READY (test 3 applied)", "DONE", "STOCK"),
                    ("test11", "READY (test 11 applied)", "DONE", "on, NO FORCED RESTART"), ("putback", "READY (stock)", "DONE", "STOCK"),
                    ("dump", "READY (stock)", None, "STOCK")], str(trail))
    sim = make_sim(files=files, emulate=emulator())
    trail = []
    for step in ("test11", "test12", "dump", "test13", "putback", "test13", "test12", "putback", "dump"):
        s, _m, sim = simulate(step, sim)
        f = s.results.get("k2", {}).get("result", {})
        trail.append((step, f.get("verdicts", [""])[-1], f.get("outcome"), (f.get("guard") or [""])[-1].split("refresh loop ")[-1]))
    check("v12 ladder: test12 goes over test11 and over test13; test13 over test12 is refused; putback clears all",
          trail == [("test11", "READY (test 11 applied)", "DONE", "on, NO FORCED RESTART"), ("test12", "READY (test 12 applied)", "DONE", "on, NO FORCED RESTART"),
                    ("dump", "READY (test 12 applied)", None, "on, NO FORCED RESTART"), ("test13", "READY (test 12 applied)", "NOT DONE", "on, NO FORCED RESTART"),
                    ("putback", "READY (stock)", "DONE", "STOCK"), ("test13", "READY (test 13 applied)", "DONE", "on, NO FORCED RESTART"),
                    ("test12", "READY (test 12 applied)", "DONE", "on, NO FORCED RESTART"), ("putback", "READY (stock)", "DONE", "STOCK"),
                    ("dump", "READY (stock)", None, "STOCK")], str(trail))
    sim = make_sim(files=files, emulate=emulator())
    trail = []
    for step in ("test12", "test14", "dump", "test15", "putback", "test15", "test14", "putback", "dump"):
        s, _m, sim = simulate(step, sim)
        f = s.results.get("k2", {}).get("result", {})
        trail.append((step, f.get("verdicts", [""])[-1], f.get("outcome"), (f.get("guard") or [""])[-1].split("refresh loop ")[-1]))
    check("v13 ladder: test14 goes over test12 and over test15; test15 over test14 is refused; putback clears all",
          trail == [("test12", "READY (test 12 applied)", "DONE", "on, NO FORCED RESTART"), ("test14", "READY (test 14 applied)", "DONE", "on, NO FORCED RESTART"),
                    ("dump", "READY (test 14 applied)", None, "on, NO FORCED RESTART"), ("test15", "READY (test 14 applied)", "NOT DONE", "on, NO FORCED RESTART"),
                    ("putback", "READY (stock)", "DONE", "STOCK"), ("test15", "READY (test 15 applied)", "DONE", "on, NO FORCED RESTART"),
                    ("test14", "READY (test 14 applied)", "DONE", "on, NO FORCED RESTART"), ("putback", "READY (stock)", "DONE", "STOCK"),
                    ("dump", "READY (stock)", None, "STOCK")], str(trail))
    check("log summary: a stalled front end is named (the start that was not taken, the link and image counters)",
          log_highlights(b"x.imgSGC:Last frame is not started.!.LnkSGC0:Last frame is not sta\nrted.d.HVcnt:D00941433,R3fff3fff 3fff3fff,L0035009c 0035\n009c 3fff3fff 3fff3fff,I3fff3fff 3fff3fff,N00000000v.")
          == ["imgSGC:Last frame is not started", "LnkSGC0:Last frame is not started", "link L0035009c 0035009c image I3fff3fff 3fff3fff"], "")
    s, _m, sim = simulate("dump", make_sim(files=files, emulate=emulator()))
    f = s.results.get("k2", {}).get("result", {})
    check("dump: TV system reported, kernel log saved",
          f.get("tv_system") == "59.94 (slot 28)" and f.get("klog_bytes", 0) > 0, str({k: f.get(k) for k in ("tv_system", "klog_bytes")}))
    check("dump: both areas of the camera's own log saved, the front end's lines picked out",
          f.get("camlog_first_bytes", 0) > 0 and f.get("camlog_last_bytes", 0) > 0 and any("DrvSgc0Start" in ln for ln in f.get("log_lines", []))
          and any(ln.startswith("HVcyc:") for ln in f.get("log_lines", [])), str(f.get("log_lines")))
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
        parser.error("name the step: dump, test1 to test15, norestart, nocheck, dfelog or putback")
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
