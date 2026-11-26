# A7 III public USB file check

Use this follow-up if the first 4.04 test returned `GET_FILE2` status `0x10000004` for `DeviceInfo.xml`. Allow about one minute. You need the A7 III, its USB data cable, and Python 3.9 or later on the computer. The test uses the computer's normal mass-storage driver and runs without administrator privileges.

1. Extract the entire tester ZIP to a folder on the computer. Keep its Windows and macOS folders together.
2. Confirm the camera menu shows **4.04**. With the USB cable disconnected, check **MENU → Setup → USB Connection → Mass Storage** and **USB LUN Setting → Multi**. Note any setting you change so you can restore it afterward.
3. Connect only this camera and wait for **PMHOME** in File Explorer or Finder. If it never appears, run the check anyway and send the resulting report. On a Windows computer where the first kit replaced the mass-storage driver with libusb, the normal volume may be unavailable. A computer using its normal mass-storage driver can run this check.
4. On **Windows**, double-click `windows/check_pmhome.cmd`. On **macOS**, open Terminal, type `bash ` (with a trailing space), drag `macos/check_pmhome.command` into the window, and press Return.
5. Send back the **M3_PMHOME_…zip** at the path printed by the launcher. It is saved in your computer's home folder, including when a read fails. Eject the camera volumes normally when finished.

The check reads only three fixed paths on the public volume. It opens each file read-only and saves the results in a ZIP on the computer. The report contains file sizes, hashes when available, and read outcomes. Sony documents the public license directory for this model. [Sony A7 III Help Guide](https://helpguide.sony.net/ilc/1720/v1/en/contents/TP0001629845.html)

| Result | Meaning |
| --- | --- |
| `control_match` | The host read `LICENSE/zlib.txt` and its bytes matched the 1,531-byte 4.04 reference. |
| `control_differs` | The host found the license file with different bytes or a different size. |
| `pmhome_not_visible`, `pmhome_not_mounted`, or `multiple_pmhome_volumes` | The test could not select one mounted PMHOME volume. |
| `missing`, `permission_denied`, or `read_error` beside an XML path | The test obtained no comparable XML at that public location. |

The checker also tests `DeviceInfo.xml` at the root and in `INFO`. Those are candidate public locations. If one matches, the exported XML has the same bytes as the 517-byte reference. A match on any public file leaves the installed imaging binary and the original service-mode read unverified.
