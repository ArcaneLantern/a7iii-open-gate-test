# A7 III open-gate test kits (firmware 4.04)

## Kit 2 (2026-11-26): first open-gate test and debug dump

**Tester steps: [K2_TEST.md](K2_TEST.md).** Kit 1 v2 confirmed that the first tester's camera runs exactly the 4.04 software and that its service file commands work. Kit 2 is the first step that changes something, and only in the camera's working memory (RAM). A battery pull undoes it.

Each step is one service session that loads a small helper library on the camera (`windows/tools/camera_tests/K2_open_gate/helper/m3og.c`, built four times). The library is written to the service work partition at `/tmp/jiritsu/libJit.so`. The camera loads it, which runs the helper once. The kit then deletes the library. The helper writes its result to the camera's RAM disk (`/ramdsk`), from where it is read back and deleted.

| Step | Windows / macOS launcher | Writes to RAM | What it does |
| --- | --- | --- | --- |
| dump | `open_gate_dump` | nothing | Kernel facts and log, where the imaging program `av-cam` sits in memory (checked against the 4.04 file), what every test byte holds, copies of the sensor and front-end tables |
| test 1 | `open_gate_test1` | 7 bytes | 4K 24p/25p full frame: the sensor reads all 4036 rows from row 61, instead of 3412 rows from row 373. The front end stays stock, so the 16:9 picture shows the sensor's top band. This tests the full-height read. |
| test 2 | `open_gate_test2` | 7 bytes + 130 words | Test 1 plus both front-end records of that mode (heights +624, vertical scaler step 6888). The whole 3:2 height is recorded squeezed into the stock 3840×2160 file. Stretch by 1.185. |
| put back | `open_gate_putback` | the 4.04 bytes | Undoes test 1 or test 2 |

**Safety rules built into the helper:**
- It writes nothing unless the program header and three code ranges in memory equal the 4.04 file.
- Every byte of the three tables it touches must hold either its 4.04 value or the step's target.
- It writes only where those two differ, reads each write back, and puts everything back on any mismatch.
- The read-only dump build contains no write call at all.

**Safety rules in the PC script:**
- Before a byte is sent, the guard refuses everything except READ_HASP, Jiritsu MOUNT/unmount, `SET_FILE_PATH` to listed paths, `GET_FILE2`, one `SET_FILE2` of the pinned library onto `/tmp/jiritsu/libJit.so`, and `FILE_DELETE2` of the library or the result.
- Each library is pinned by SHA-256 in `m3og.py`.

The test design (`og_m3_v1`) comes from the 4.04 firmware:
- The IMX410 register list sets each drive mode's vertical window (registers 0x0728–0x072B).
- The LEO front-end record of the 4K full-frame mode holds 65 height fields and the vertical scaler step.
- The firmware's own register-list code, run in an emulator, programs the new window. The four helper builds were run in an emulator against the 4.04 memory image: 39 checks, including roll-back and every refusal.

None of this has run on an A7 III yet.

Commands, from `windows` (after `setup.cmd`):

    .venv\Scripts\python.exe -I -B tools\camera_tests\K2_open_gate\m3og.py --selftest
    .venv\Scripts\python.exe -I -B tools\camera_tests\K2_open_gate\m3og.py test2 --dry-run
    .venv\Scripts\python.exe -I -B tools\camera_tests\K2_open_gate\m3og.py dump --go --firmware-shown 4.04

## Kit 1 v2: service-mode file check (done: `4.04 CONFIRMED` on the first tester's camera)

**Kit 1 v2 (2026-11-26).** The first run of kit 1 logged in to service mode, then its first file read answered `0x10000004`. The 4.04 firmware explains why. Every service file command mounts the camera's service work area (`/dev/nflasha6` on `/tmp/jiritsu`). Only Sony's own Jiritsu MOUNT command creates that folder, and kit 1 v1 never sent it, because the A7 IV kits it came from do not need it. v2 sends MOUNT before the reads and always sends the matching unmount afterwards. Short tester steps: [K1V2_TEST.md](K1V2_TEST.md). The [public USB file check](PMHOME_TEST.md) has already been done (`control_match`).

This is the first camera step of a study of the Sony A7 III (ILCE-7M3) firmware 4.04. The study's goals are open gate (full-height 3:2 video), the video encoder, and 10-bit recording.

**This kit writes no camera file, setting or memory.** For the length of the run, the camera's service work area is mounted, as Sony's own service software does. At the end it is unmounted and its folder removed.

It answers four questions before anything else is built for this camera:

1. Does the A7 III accept the USB service-mode login used by the A7 IV and A7S III kits?
2. Do its file-read commands answer?
3. Is the camera's software byte for byte the 4.04 update the study was made from?
4. Which memory configuration file is installed?

Everything later (memory reads, then any patch) depends on these answers.

## What it does

One USB session with the camera in Mass Storage mode:

1. It switches the camera to service mode and logs in. This uses the public procedure from Sony-PMCA-RE, the same as the A7 IV and A7S III kits.
2. It reads the product information (`READ_HASP`).
3. It mounts the service work area (Jiritsu MOUNT): this creates the folder `/tmp/jiritsu` and mounts `/dev/nflasha6` there.
4. It reads these files and compares each with the 4.04 update (size and SHA-256 checksum):

   | File | Why |
   |---|---|
   | `/usr/share/pmbp/DeviceInfo.xml` | known answer: if it differs, nothing more is read |
   | `/usr/lib/libJiritsu.so`, `/usr/lib/libsencore.so` | the service-mode libraries |
   | `/usr/codec/vcd_firmware.bin` | the video codec's firmware |
   | `/system/av-cam.bin` (18 MB) | the imaging and recording program |
   | `/setting/DmmConfig.bin` | memory configuration; may be missing |
   | `/proc/cpuinfo`, `/proc/iomem` | expected to come back empty |

5. It always unmounts the work area and removes `/tmp/jiritsu` (Jiritsu MOUNT, unmount form), even if a read failed.
6. It always ends with the stop request. The camera then leaves service mode; switch it off and on if it does not return to normal.

Only four service commands can be sent:
- `READ_HASP`;
- Jiritsu MOUNT, with exactly the mount and unmount payloads for the work area (never the memory card);
- `SET_FILE_PATH`, for the paths above only;
- `GET_FILE2`.

The script refuses anything else before a byte leaves the PC: write, delete, format, firmware, settings and memory commands. `selftest.cmd` shows this.

The settings backup is **not** read, because it would carry personal data. Large files are not saved, only their size and checksum.

## Before you start

1. The camera's menu must show **Ver. 4.04** (MENU → Setup → Version). On any other version, stop and tell us the version.
2. **USB Connection Mode: Mass Storage** (MENU → Setup → USB Connection). Note your current setting so you can put it back.
3. A charged battery and a memory card in the camera.
4. Unplug other Sony USB devices from the PC.

## Windows, once

1. Install Python 3.10 or later from python.org, with the "py launcher".
2. Run `windows/setup.cmd`.
3. Run `windows/selftest.cmd`. It needs no camera and must end with `0 failed`. It also prints every packet the real run would send.
4. Install the libusb-win32 driver for the camera with [Zadig](https://zadig.akeo.ie):
   - Connect the camera (Mass Storage), then in Zadig: Options → List All Devices, pick the camera, choose libusb-win32, Replace Driver.
   - The first run switches the camera to service mode, where it shows up as a new device, probably `054C:0336`. It does not stay there long enough to do this by hand. So beforehand, in Zadig: Device → Create New Device, any name, USB ID `054C` `0336`, libusb-win32, Install Driver.
   - `windows/list_devices.cmd` shows what Windows and libusb see. It sends nothing.

## macOS users

1. You must have python 3.10 or later (if you have Xcode Tools that works too, run xcode-select --install in terminal if you're unsure)
2. Run macos/setup.command by dragging it into your terminal window, running it directly from finder usually results in a ton of permissions errors.
3. Run macos/selftest.command the same way.
4. Run macos/list_devices.command the same way too.
5. Run macos/check_readonly.command. This runs kit 1 v2 (the service-mode file check).

## The run

1. Camera on, Mass Storage mode, connected.
2. Run `windows/check_readonly.cmd` and type the version the camera's menu shows (`4.04`).
3. On a first run it may stop with "EXPECTED on a first run: … no libusb driver yet". Leave the camera on and connected, do the Zadig step for the service device, and run again.
4. The end of the output shows the verdict: `4.04 CONFIRMED`, `NOT MATCHING: <files>` or `UNVERIFIED: …`.

## Please send back

The newest folder in `windows/camera_private` (zip it), and one line on what the camera's screen showed during and after the run. The folder holds:
- `transcript.jsonl` (everything printed and every USB exchange);
- `manifest.json` (results);
- the small files read.

Serial numbers are masked in the device listings.

## What is known so far (static analysis of the 4.04 update)

- The A7 III's service library holds the same login keys as the A7 IV's. Its file commands have the same command numbers.
- Its video codec is the A7 IV's codec family. The codec firmware has a complete 10-bit path, and the camera's encoder tables already contain 10-bit 4:2:2 rows that its menus never use.
- The sensor's 4K 24p full-width read-out takes about 25 ms. A full-height read-out would fit a 24p frame.

On the first tester's camera, the service-mode login and `READ_HASP` worked (kit 1 v1). The built-in PMHOME volume matches 4.04 (public USB file check). Kit 1 v2 confirmed 4.04 and the service file route. Kit 2 is the next step.

## Licence and third-party code

`windows/tools/third_party/sony-pmca-re` holds the unmodified USB transport files of [Sony-PMCA-RE](https://github.com/ma1co/Sony-PMCA-RE), pinned by checksum (`PINNED.json`). The `CT1_usb_first_contact` scripts are the A7 IV / A7S III kits' guarded USB layer, copied unchanged (`PROVENANCE.json`). No Sony firmware file is included. Kit 1 carries only sizes and checksums. Kit 2's helper (`m3og_design.h`, and the four libraries built from it) carries the 4.04 contents of the three small tables it checks and changes: the sensor register list (5,496 bytes) and two front-end records (1,344 bytes each), plus checksums of three code ranges.
