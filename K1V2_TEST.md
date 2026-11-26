# A7 III kit 1 v2: service-mode file check

This repeats the first kit's run with one fix. Allow about five minutes. You need the A7 III on firmware 4.04, a charged battery, a memory card in the camera, and its USB data cable.

**Why again.** Your first run logged in to service mode, but the file reads answered `0x10000004`. The A7 III needs one extra Sony service step before it can read files: mounting its service work area. The A7 IV kits that kit 1 came from never needed it. v2 adds that step and undoes it at the end.

**What it changes.** It writes no camera file, setting or memory. During the run, a temporary folder exists and the service work area is mounted there. Both are removed at the end, before the camera leaves service mode.

## macOS

1. Download the repo again as a ZIP and extract all of it to a new folder.
2. Turn the camera **off and on**. Check **MENU → Setup → Version** shows **4.04** and **USB Connection** is **Mass Storage**.
3. Connect the camera straight to the Mac (no hub or dock). Click **Allow** if macOS asks about the accessory.
4. In Terminal, type `bash ` (with a trailing space), drag `macos/setup.command` into the window, and press Return. Do this once for the new folder.
5. The same way, run `macos/selftest.command`. It needs no camera and must end with `0 failed`.
6. The same way, run `macos/check_readonly.command`. Type `4.04` when asked. Enter your Mac password when asked: macOS needs it to take the camera over from Finder.
7. Wait until it prints the verdict and "Press Return to close". Reading the 18 MB program file takes a minute or two. Don't unplug the camera while it runs.
8. Turn the camera off and on again.
9. Zip the newest `M3K1v2_…` folder in `windows/camera_private` and send it back. Add one line on what the camera's screen showed during and after the run.

## Windows

Use `windows/setup.cmd` and `windows/selftest.cmd`, then `windows/check_readonly.cmd`. The Zadig driver steps in the README are the same as for the first kit. Then do steps 7 to 9 above.

## Verdicts

| Verdict | Meaning |
| --- | --- |
| `4.04 CONFIRMED` | Every required file equals the 4.04 update. |
| `NOT MATCHING: …` | The listed files differ from 4.04. |
| `UNVERIFIED: … 0x10000004 …` | The service work area still could not be mounted. |
| `UNVERIFIED: …` (other) | A read failed. The saved folder shows where. |
