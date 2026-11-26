# A7 III kit 2: first open-gate test

Allow about 40 minutes. You need the A7 III on firmware 4.04, a charged battery, a memory card with free space, and its USB data cable. The setup from kit 1 (Python, and on Windows the Zadig driver) still applies.

**What this is.** Kit 1 showed that your camera runs exactly the 4.04 software and that its service file commands work. Kit 2 is the first step that changes something. It loads a small helper on the camera, once per step, which changes a few bytes of the camera's working memory (RAM). It never writes to the camera's firmware or settings.

**How to undo it.** Take the battery out for ten seconds. The camera then reloads its program from its own flash, as stock. The `putback` step does the same without removing the battery. The power switch alone is **not** enough on this camera family, so always end with a battery pull.

## The four steps

| Step | Launcher | What it does |
| --- | --- | --- |
| dump | `open_gate_dump` | Read-only. Saves facts about the camera's memory, its kernel log, and what the test bytes hold now. Writes nothing to memory. |
| test 1 | `open_gate_test1` | 7 bytes. In 4K 24p (25p on PAL) full frame, the sensor reads its whole height instead of the 16:9 band. The rest of the chain is stock, so the recorded picture shows the **top band** of the sensor instead of the middle. It is a shift, not a taller picture yet. This tests whether the camera survives a full-height read. |
| test 2 | `open_gate_test2` | Test 1 plus the front-end chip's settings for that mode. The whole 3:2 sensor height is recorded **squeezed** into the normal 3840×2160 file. Round things look about 1.19 times wider. Stretch the clip vertically by 1.185 to see it right. |
| put back | `open_gate_putback` | Puts the 4.04 bytes back. |

Windows launchers are `windows/<name>.cmd`. On macOS, type `bash ` (with a trailing space), drag `macos/<name>.command` into Terminal, and press Return. Every step asks for the firmware version (type `4.04`). The writing steps also ask you to type `YES`. On macOS, enter your password when asked.

## Before you start

1. Download the repo again as a ZIP and extract all of it to a new folder. Run `setup` once for that folder, then `selftest`. Self-test needs no camera and must end with `0 failed` (twice).
2. On the camera: **MENU → Setup → USB Connection: Mass Storage**. For the movie part, set **File Format: XAVC S 4K**, **Record Setting: 24p 100M** (or 60M; on a PAL camera 25p), and **APS-C/Super 35mm: Off**. Manual focus is easiest, because autofocus may aim at the wrong place in the tests.
3. Connect the camera straight to the computer, with no hub or dock.

## Test 1

1. **Battery out for ten seconds**, then back in, and turn the camera on. Put the mode dial on a stills mode (P, A, S, M or Auto). Connect USB.
2. Run **dump**. It should end with `VERDICT READY (stock)`. If it says anything else, stop here and send the folder.
3. Run **test 1**. Type `YES`. It should show `Outcome: DONE` and `VERDICT READY (test 1 applied)`.
4. Unplug USB. Turn the dial to **movie**. Point the camera at something with clear top and bottom edges. Compared with a normal 4K picture, the view should be shifted up or down by about a tenth of the frame. Record about **10 seconds**.
5. Write down what you saw: normal, shifted, frozen, garbled, black, or the camera restarted by itself.
6. What next:
   - **The camera restarted by itself:** do not pull the battery. Connect USB and run **dump** at once: the kernel log of the failed start is still in memory. Then go to step 8.
   - **The picture froze and the camera does not respond:** take the battery out (the log is lost then). Go to step 8.
   - **Otherwise:** turn the dial back to a stills mode, connect USB, and run **dump**. Then run **put back**.
7. Put back should end with `VERDICT READY (stock)`.
8. **Battery out for ten seconds.**

## Test 2

The same as test 1, with **test 2** in step 3. In step 4 the movie view should show more of the scene from top to bottom, squeezed so that people look shorter and wider.

## Please send back

- The newest `M3K2_…` folders in `windows/camera_private`, zipped. Each step makes one folder, ending in its step name.
- One line per test on what the screen showed in movie mode.
- The two clips, or a frame from each. The 10 seconds from test 2 are the important one.

The dump holds the camera's kernel log as text. MAC addresses in it are blanked, and the processor's serial line is not copied. Device listings mask serial numbers.

## Results the steps can print

| Line | Meaning |
| --- | --- |
| `VERDICT READY (stock)` | The camera's program is exactly 4.04, in the place the kit expects, and none of the test bytes are changed. |
| `VERDICT READY (test 1 applied)` / `(test 2 applied)` | That test's bytes are in place. |
| `VERDICT NOT READY …` | The kit did not find the 4.04 program where it expected it, or the bytes are partly changed. Nothing is written in that state. |
| `Outcome: DONE` | The step wrote its bytes and read each back. |
| `Outcome: NOT DONE …` | Nothing was written, or everything written was put back. The line says why. Running test 1 while test 2 is applied gives this. Run put back first. |
| `Outcome: NOTHING TO DO` | The bytes already were what this step writes. |
| `!! UNDO INCOMPLETE` | Take the battery out for ten seconds now. |
