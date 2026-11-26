# A7 III public USB file check

Use this follow-up if the first 4.04 test returned `GET_FILE2` status `0x10000004` for `DeviceInfo.xml`. Allow about one minute. You need the A7 III, its USB data cable, and Python 3.9 or later on the computer. The test uses the computer's normal mass-storage driver and runs without administrator privileges.

**Version 2 (M3_PMHOME_v2).** If your report said `pmhome_not_visible`, please run this version once. Version 1 searched the computer's external disks only for a volume named PMHOME, and it saved nothing else. Version 2 finds the camera through the same USB route the first test used on your computer, then checks every disk the camera shows. It saves a short list of what the computer saw, so the report is useful even if PMHOME does not appear.

1. Extract the entire tester ZIP to a folder on the computer. Keep its Windows and macOS folders together.
2. **Turn the camera off and on again.** At the end of the first test the camera leaves the USB bus, so start from a fresh power-on.
3. Confirm the camera menu shows **4.04**. With the USB cable disconnected, check **MENU → Setup → USB Connection → Mass Storage** and **USB LUN Setting → Multi**. Note any setting you change so you can restore it afterward.
4. Connect only this camera, straight to the computer (no hub or dock). On a Mac, click **Allow** if macOS asks whether to allow the accessory. Wait for **PMHOME** in File Explorer or Finder. If it never appears, run the check anyway and send the resulting report. On a Windows computer where the first kit replaced the mass-storage driver with libusb, the normal volume may be unavailable. A computer using its normal mass-storage driver can run this check.
5. On **Windows**, double-click `windows/check_pmhome.cmd`. On **macOS**, open Terminal, type `bash ` (with a trailing space), drag `macos/check_pmhome.command` into the window, and press Return.
6. Send back the **M3_PMHOME_…zip** at the path printed by the launcher. It is saved in your computer's home folder, including when a read fails. Eject the camera volumes normally when finished.

The check reads only three fixed paths on the public volume. It opens each file read-only and saves the results in a ZIP on the computer. It mounts, unmounts, renames and writes nothing. The report contains:

- file sizes, hashes when available, and read outcomes;
- the Sony USB id and interface classes;
- the camera's disks, with size, file system and whether each is mounted.

It also includes a count of other disks. Volume names are kept only when they are PMHOME, NO NAME or Untitled. It saves no serial number, other volume name or file listing. Sony documents the public license directory for this model. [Sony A7 III Help Guide](https://helpguide.sony.net/ilc/1720/v1/en/contents/TP0001629845.html)

| Result | Meaning |
| --- | --- |
| `control_match` | The host read `LICENSE/zlib.txt` and its bytes matched the 1,531-byte 4.04 reference. |
| `control_differs` | The host found the license file with different bytes or a different size. |
| `camera_not_on_usb` | The computer shows no Sony USB device. Turn the camera off and on, reconnect without a hub, and allow the accessory. |
| `camera_in_service_mode` | The camera still shows the first test's service mode (`054c:0336`). Turn it off and on, then reconnect. |
| `camera_in_mtp_or_remote_mode` or `camera_not_in_mass_storage` | The camera is connected, but not as a disk. Set **USB Connection → Mass Storage** and reconnect. |
| `camera_disks_absent` | The camera is in Mass Storage mode but shows no disks yet. Reconnect and run again. |
| `pmhome_not_mounted` | The built-in disk is attached but not mounted. Reconnect and run again. Do not repair or format it. |
| `pmhome_not_visible` or `multiple_pmhome_volumes` | The camera's disks were listed, but the test could not select one built-in PMHOME volume. |
| `missing`, `permission_denied`, or `read_error` beside an XML path | The test obtained no comparable XML at that public location. |

The output line `volume … (found by …)` shows how the volume was recognised:

- `name`: its label is PMHOME;
- `control_file`: `LICENSE/zlib.txt` is at its root;
- `size`: it is the small built-in disk, about 2 MiB.

The checker also tests `DeviceInfo.xml` at the root and in `INFO`. Those are candidate public locations. If one matches, the exported XML has the same bytes as the 517-byte reference. A match on any public file leaves the installed imaging binary and the original service-mode read unverified.
