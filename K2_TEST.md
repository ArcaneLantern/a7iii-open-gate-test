# A7 III kit 2 v5: open-gate timing read

**If you ran kit 2 v4:** thank you. That run told us three things.

- The camera's picture check trips because the picture's timing signal arrives in the wrong frame, not because the picture is missing.
- With the restart switched off the camera stays on but stutters, because the check restarts the picture every frame.
- With the check switched off the picture is jittery and dark. So the check is right that something is off, and switching it off is not the fix.

One thing went differently from the page: put back was skipped before test 2, so test 2 answered `NOT DONE` and nothing was written. The last try was test 4 again, which is why it looked the same. Nothing went wrong; the kit refuses one test on top of another.

**What this run is for.** The dump can see the timing of the last frame the camera made before USB was plugged in. So this time the dumps are taken **with the dial left on movie**. Three dumps (stock, test 4, test 2) show how far the timing signal moves with the picture height. That is the number we need to fix it properly.

Allow about 30 minutes. You need the A7 III on firmware 4.04, a charged battery, a memory card, and its USB data cable.

**How to undo it.** The `putback` step, or taking the battery out for ten seconds, puts the camera back to stock. The power switch alone is **not** enough.

## The steps used

| Step | Launcher | What it does |
| --- | --- | --- |
| dump | `open_gate_dump` | Read-only. Saves the camera's memory facts and the timing of the last frame. |
| test 4 | `open_gate_test4` | A quarter of the extra height (the smallest change). |
| test 2 | `open_gate_test2` | The whole 3:2 sensor height. |
| no restart | `open_gate_norestart` | One bit. The camera's check keeps retrying but never restarts the camera. |
| put back | `open_gate_putback` | Puts the 4.04 bytes back and clears the switch. |

Windows launchers are `windows/<name>.cmd`. On macOS, type `bash ` (with a trailing space), drag `macos/<name>.command` into Terminal, and press Return. Every step asks for the firmware version (type `4.04`). Every step except dump also asks you to type `YES`.

## Before you start

1. Download the repo again as a ZIP and extract all of it to a new folder. Run `setup` once for that folder, then `selftest`. It must end with `0 failed` (twice).
2. On the camera: **USB Connection: Mass Storage**, **File Format: XAVC S 4K**, **Record Setting: 24p 60M** (25p on a PAL camera), **APS-C/Super 35mm: Off**.

## The run

**The rule this time:** unplug the USB cable before each movie try. Plug it back in **while the dial is still on movie**. Test steps and put back are run with the dial on a stills mode, as before.

### Part A: stock

1. **Battery out for ten seconds**, then back in. Turn the camera on.
2. Cable unplugged. Turn the dial to **movie**. Wait about 10 seconds with the normal picture on the screen.
3. Leave the dial on movie. Plug in USB. Run **dump**. It should end with `VERDICT READY (stock)`.

### Part B: test 4

4. Turn the dial to a stills mode. Run **test 4**, then **no restart**. Check both say `Outcome: DONE`.
5. Unplug USB. Turn the dial to **movie**. Wait about 10 seconds (the picture will stutter, as last time).
6. Leave the dial on movie. Plug in USB. Run **dump**. It should say `VERDICT READY (test 4 applied)`.
7. Turn the dial to a stills mode. Run **put back**. It must end with `VERDICT READY (stock)`. Do not skip this one.

### Part C: test 2

8. Run **test 2**, then **no restart**. Check both say `Outcome: DONE`. If test 2 says `NOT DONE`, run put back and try again.
9. Unplug USB. Turn the dial to **movie**. Wait about 10 seconds.
10. Leave the dial on movie. Plug in USB. Run **dump**. It should say `VERDICT READY (test 2 applied)`.
11. Turn the dial to a stills mode. Run **put back**.
12. **Battery out for ten seconds** to finish.

**If the camera freezes and does not respond at any point:** take the battery out for ten seconds, note where it happened, and go on with the next part.

## Please send back

- All the new `M3K2_…` folders in `windows/camera_private`, zipped. There should be three ending in `_dump`.
- One line per part on what the screen showed.
- The videos you already recorded are welcome when they are ready. No new clips are needed for this run.

**Please send the zips privately, not in a public channel.** The dump copies parts of the camera's working memory and its kernel log as text. MAC addresses in the log are blanked and the processor's serial line is not copied, but we cannot promise that nothing else in there identifies the camera.

## Results the steps can print

| Line | Meaning |
| --- | --- |
| `VERDICT READY (stock)` | The camera's program is exactly 4.04 and none of the test bytes are changed. |
| `VERDICT READY (test N applied)` | That test's bytes are in place. |
| `VERDICT NOT READY …` | The kit did not find the 4.04 program where it expected it, or the bytes are partly changed. Nothing is written in that state. |
| `Refresh-loop switch: … STOCK` / `NO FORCED RESTART` / `OFF` | What the camera's own switch for the check is set to. |
| `Last frame before USB: …` | The timing the dump read. Nothing to do with it; it is for us. |
| `Outcome: DONE` | The step wrote its bytes and read each back. |
| `Outcome: NOT DONE …` | Nothing was written. The line says why. One test on top of another gives this: run put back first. |
| `Outcome: NOTHING TO DO` | The bytes already were what this step writes. |
| `!! UNDO INCOMPLETE` | Take the battery out for ten seconds now. |
