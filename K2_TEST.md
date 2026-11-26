# A7 III kit 2 v4: open-gate test

**If you ran kit 2 v3:** thank you. Your report was exactly what we needed.

- All three tests showed the open-gate picture for about a second. So the picture path works at every height, including the full 3:2 one.
- All three then restarted at the same place. That place is not a crash in the usual sense. The camera has a check that watches the picture's timing signal. When the check is unhappy it restarts the picture, and after ten tries in a row it restarts the whole camera on purpose.
- The camera's software has two switches of its own for that check. v4 adds them as steps, so we can see what the check is doing and whether the picture is good without it.

Download the repo again and do the page below from the start.

Allow about 40 minutes. You need the A7 III on firmware 4.04, a charged battery, a memory card with free space, and its USB data cable. The setup from kit 1 (Python, and on Windows the Zadig driver) still applies.

**What this is.** Each step loads a small helper on the camera once. A test step changes some bytes of the camera's working memory (RAM). Nothing is written to the camera's firmware or settings.

**How to undo it.** Any of these puts the camera back to stock: the `putback` step, a restart the camera does by itself, or taking the battery out for ten seconds. The power switch alone is **not** enough on this camera family.

## The steps

| Step | Launcher | What it does |
| --- | --- | --- |
| dump | `open_gate_dump` | Read-only. Saves facts about the camera's memory and what the test bytes hold now. New: it also reads how often the check retried. |
| test 4 | `open_gate_test4` | A quarter of the extra height, squeezed into the normal 3840×2160 file (squeeze 1.05). The smallest change. |
| test 2 | `open_gate_test2` | The whole 3:2 sensor height, squeezed (1.19). The one we are after. |
| no restart | `open_gate_norestart` | One bit. The check keeps retrying, but it never restarts the camera. |
| no check | `open_gate_nocheck` | One bit. The check is switched off. |
| put back | `open_gate_putback` | Puts the 4.04 bytes back and clears both switches. |

Test 1 and test 3 are still in the kit. You do not need them this time.

Windows launchers are `windows/<name>.cmd`. On macOS, type `bash ` (with a trailing space), drag `macos/<name>.command` into Terminal, and press Return. Every step asks for the firmware version (type `4.04`). Every step except dump also asks you to type `YES`. On macOS, enter your password when asked.

## Before you start

1. Download the repo again as a ZIP and extract all of it to a new folder. Run `setup` once for that folder, then `selftest`. Self-test needs no camera and must end with `0 failed` (twice).
2. On the camera: **MENU → Setup → USB Connection: Mass Storage**. For the movie part, set **File Format: XAVC S 4K**, **Record Setting: 25p 60M** on a PAL camera (24p on NTSC), and **APS-C/Super 35mm: Off**. Manual focus is easiest.
3. Connect the camera straight to the computer, with no hub or dock.

## The run

**Every step is run with the mode dial on a stills mode (P, A, S, M or Auto).** Turn the dial to movie only when the page says so.

**If the picture freezes and the camera does not respond at any point:** take the battery out for ten seconds, note where it happened, and go on with the next part.

### Part A: the smallest test, with the restart switched off

1. **Battery out for ten seconds**, then back in. Turn the camera on, dial on a stills mode, connect USB.
2. Run **dump**. It should end with `VERDICT READY (stock)` and `Refresh-loop switch: … STOCK`.
3. Run **test 4**. It should show `Outcome: DONE` and `VERDICT READY (test 4 applied)`.
4. Run **no restart**. It should show `Outcome: DONE` and `Refresh-loop switch: … NO FORCED RESTART`.
5. Turn the dial to **movie** and watch the screen for about 15 seconds. The camera should now stay on. Note what the picture does: steady, or a hiccup or flicker again and again. Record about **5 seconds**. Take a phone photo of the screen.
6. Turn the dial back to a stills mode. Run **dump**. Do not run put back yet.

### Part B: the same test, with the check switched off

7. Run **no check**. It should show `Refresh-loop switch: … OFF`.
8. Turn the dial to **movie**. Watch for about 15 seconds: is the picture steady now? Record about **5 seconds**. Take a phone photo of the screen.
9. Turn the dial back to a stills mode. Run **dump**, then **put back**. Put back should end with `VERDICT READY (stock)` and `Refresh-loop switch: … STOCK`.

### Part C: the full height, with the check switched off

Do this part if part B gave a picture.

10. Run **test 2**, then **no check**.
11. Turn the dial to **movie**. Watch for about 15 seconds, record about **5 seconds**, take a phone photo of the screen.
12. Turn the dial back to a stills mode. Run **dump**, then **put back**.
13. **Battery out for ten seconds** to finish.

## Please send back

- All the new `M3K2_…` folders in `windows/camera_private`, zipped.
- For each of the three movie tries, one line on what the picture did: steady, repeated hiccup, flicker, frozen, restarted.
- For each try that gave a picture, either a phone photo of the camera's screen or a screenshot of one frame of the clip (open the clip on your computer, pause it, take a screenshot). If a clip plays back strangely on the computer (jumps, repeated frames), say so.

**Please send the zips privately, not in a public channel.** The dump copies parts of the camera's working memory and its kernel log as text. MAC addresses in the log are blanked and the processor's serial line is not copied, but we cannot promise that nothing else in there identifies the camera.

## Results the steps can print

| Line | Meaning |
| --- | --- |
| `VERDICT READY (stock)` | The camera's program is exactly 4.04, in the place the kit expects, and none of the test bytes are changed. |
| `VERDICT READY (test N applied)` | That test's bytes are in place. |
| `VERDICT NOT READY …` | The kit did not find the 4.04 program where it expected it, could not tell the camera's TV system, or the bytes are partly changed. Nothing is written in that state. |
| `Refresh-loop switch: … STOCK` / `NO FORCED RESTART` / `OFF` | What the camera's own switch for the check is set to. |
| `Outcome: DONE` | The step wrote its bytes and read each back. |
| `Outcome: NOT DONE …` | Nothing was written, or everything written was put back. The line says why. Running one test while another is applied gives this: run put back first. |
| `Outcome: NOTHING TO DO` | The bytes already were what this step writes. |
| `!! UNDO INCOMPLETE` | Take the battery out for ten seconds now. |
