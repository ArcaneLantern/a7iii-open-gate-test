# A7 III kit 2 v3: open-gate test

**If you ran kit 2 v2:** thank you, that run answered a lot.

- Test 1 worked: the sensor can read its whole height at 24p.
- Test 2 made the camera restart when movie mode started. The dump you took right after showed why. The camera's own software noticed that no picture was arriving, tried ten times to restart the picture, and then restarted itself. That restart also put everything back to stock, with no battery pull.
- The cause, as far as the camera's software shows it: test 2 changed the picture height in one place but not in the camera's frame timing for that mode. v3 changes both together.

Download the repo again and do the page below from the start.

Allow about 30 minutes. You need the A7 III on firmware 4.04, a charged battery, a memory card with free space, and its USB data cable. The setup from kit 1 (Python, and on Windows the Zadig driver) still applies.

**What this is.** Each step loads a small helper on the camera once. A test step changes some bytes of the camera's working memory (RAM). Nothing is written to the camera's firmware or settings.

**How to undo it.** Any of these puts the camera back to stock: the `putback` step, a restart the camera does by itself, or taking the battery out for ten seconds. The power switch alone is **not** enough on this camera family.

## The steps

| Step | Launcher | What it does |
| --- | --- | --- |
| dump | `open_gate_dump` | Read-only. Saves facts about the camera's memory, its two logs, and what the test bytes hold now. |
| test 2 | `open_gate_test2` | The whole 3:2 sensor height, recorded **squeezed** into the normal 3840×2160 file. Round things look 1.19 times wider. This is the one we hope works. The camera has to process lines 15 % faster than in any stock mode, so it may not keep up. |
| test 3 | `open_gate_test3` | Half the extra height (squeeze 1.09, lines 6 % faster). Only needed if test 2 restarts. |
| test 4 | `open_gate_test4` | A quarter of the extra height (squeeze 1.05, lines 2 % faster). Only needed if test 3 restarts. |
| put back | `open_gate_putback` | Puts the 4.04 bytes back. |
| test 1 | `open_gate_test1` | The sensor change alone, as in v2. It already passed; you do not need to run it again. |

Windows launchers are `windows/<name>.cmd`. On macOS, type `bash ` (with a trailing space), drag `macos/<name>.command` into Terminal, and press Return. Every step asks for the firmware version (type `4.04`). The test steps and put back also ask you to type `YES`. On macOS, enter your password when asked.

## Before you start

1. Download the repo again as a ZIP and extract all of it to a new folder. Run `setup` once for that folder, then `selftest`. Self-test needs no camera and must end with `0 failed` (twice).
2. On the camera: **MENU → Setup → USB Connection: Mass Storage**. For the movie part, set **File Format: XAVC S 4K**, **Record Setting: 24p 60M** (or 100M; on a PAL camera 25p), and **APS-C/Super 35mm: Off**. Manual focus is easiest.
3. Connect the camera straight to the computer, with no hub or dock.

## The run

**Every step is run with the mode dial on a stills mode (P, A, S, M or Auto).** Turn the dial to movie only when the page says so.

1. **Battery out for ten seconds**, then back in. Turn the camera on, dial on a stills mode, connect USB.
2. Run **dump**. It should end with `VERDICT READY (stock)`. It also prints the TV system it found (59.94 or 50). If the verdict says anything else, stop and send the folder.
3. Run **test 2**. Type `YES`. It should show `Outcome: DONE` and `VERDICT READY (test 2 applied)`.
4. Turn the dial to **movie**. Point the camera at something with clear top and bottom edges. Now look at the screen:

   - **A picture that shows more of the scene from top to bottom, with everything looking shorter and wider:** this is the result we are after. Record about **5 seconds**. Take a phone photo of the camera's screen too. Then go to step 5.
   - **The camera restarts by itself** (as last time): leave the battery in. Turn the dial back to a stills mode and run **dump** straight away, before anything else. The camera's log of what went wrong is still in memory. Then repeat steps 3 and 4 with **test 3**. If that restarts as well, dump again and repeat with **test 4**.
   - **The picture freezes and the camera does not respond:** take the battery out for ten seconds, start again at step 1, and use the next smaller test.

5. When a test gives a picture: turn the dial back to a stills mode, run **dump**, then run **put back**. Put back should end with `VERDICT READY (stock)`.
6. **Battery out for ten seconds** to finish.

If test 2 works you are done. There is no need to run test 3 or test 4.

## Please send back

- All the new `M3K2_…` folders in `windows/camera_private`, zipped. Each step makes one folder, ending in its step name.
- One line per test on what the screen showed in movie mode.
- A picture from each test that gave one. A clip is too large for most chat apps, so either of these is fine:
  - a phone photo of the camera's screen, or
  - a screenshot of one frame: open the clip on your computer, pause it, and take a screenshot.
- If you still have the clip from **test 1** of the last run: a screenshot of one frame. We could not see whether the picture was shifted up or down, which is what test 1 should have shown.

**Please send the zips privately, not in a public channel.** The dump now also copies the camera's own application log as text. MAC addresses in it are blanked and the processor's serial line is not copied, but we have not seen this log before and cannot promise it holds nothing else that identifies the camera, such as a serial number or a Wi-Fi network name.

## Results the steps can print

| Line | Meaning |
| --- | --- |
| `VERDICT READY (stock)` | The camera's program is exactly 4.04, in the place the kit expects, and none of the test bytes are changed. |
| `VERDICT READY (test N applied)` | That test's bytes are in place. |
| `VERDICT NOT READY …` | The kit did not find the 4.04 program where it expected it, could not tell the camera's TV system, or the bytes are partly changed. Nothing is written in that state. |
| `Outcome: DONE` | The step wrote its bytes and read each back. |
| `Outcome: NOT DONE …` | Nothing was written, or everything written was put back. The line says why. Running one test while another is applied gives this: run put back first. |
| `Outcome: NOTHING TO DO` | The bytes already were what this step writes. |
| `!! UNDO INCOMPLETE` | Take the battery out for ten seconds now. |
