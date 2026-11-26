# A7 III test kit 1: read-only check (firmware 4.04)

This is the first camera step of a study of the Sony A7 III (ILCE-7M3) firmware 4.04. The study's goals are open gate (full-height 3:2 video), the video encoder, and 10-bit recording.

**This kit only reads. It changes nothing in the camera: no setting, no file, no memory.**

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
3. It reads these files and compares each with the 4.04 update (size and SHA-256 checksum):

   | File | Why |
   |---|---|
   | `/usr/share/pmbp/DeviceInfo.xml` | known answer: if it differs, nothing more is read |
   | `/usr/lib/libJiritsu.so`, `/usr/lib/libsencore.so` | the service-mode libraries |
   | `/usr/codec/vcd_firmware.bin` | the video codec's firmware |
   | `/system/av-cam.bin` (18 MB) | the imaging and recording program |
   | `/setting/DmmConfig.bin` | memory configuration; may be missing |
   | `/proc/cpuinfo`, `/proc/iomem` | expected to come back empty |

4. It always ends with the stop request. The camera then leaves service mode; switch it off and on if it does not return to normal.

Only three service commands can be sent: `READ_HASP`, `SET_FILE_PATH` (for the paths above only) and `GET_FILE2`. The script refuses anything else before a byte leaves the PC: write, delete, format, settings commands, memory commands. `selftest.cmd` shows this.

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
5. Run macos/check_readonly.command. This reads all the read only data required for testing.

## The run

1. Camera on, Mass Storage mode, connected.
2. Run `windows/check_readonly.cmd` and type the version the camera's menu shows (`4.04`).
3. On a first run it may stop with "EXPECTED on a first run: … no libusb driver yet". Leave the camera on and connected, do the Zadig step for the service device, and run again.
4. The end of the output shows the verdict: `4.04 CONFIRMED` or `NOT MATCHING: <files>`.

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

None of this has been tried on a camera. This kit is the first contact.

## Licence and third-party code

`windows/tools/third_party/sony-pmca-re` holds the unmodified USB transport files of [Sony-PMCA-RE](https://github.com/ma1co/Sony-PMCA-RE), pinned by checksum (`PINNED.json`). The `CT1_usb_first_contact` scripts are the A7 IV / A7S III kits' guarded USB layer, copied unchanged (`PROVENANCE.json`). No Sony firmware is included, only sizes and checksums.
