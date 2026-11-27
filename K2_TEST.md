# A7 III kit 2 v8: one short test

**If you ran kit 2 v7:** thank you. Test 5 gave exactly the same frame as test 3: the picture stops at the same row, then the black bar, then the thin strip. So the camera's picture-height note is not what cuts the picture short, and that idea is closed.

**What we now think.** In every test the picture ends at the same place on the sensor as in a stock camera. We start reading higher up and ask for more rows, but the rows below the stock bottom edge never arrive. The new **test 6** checks exactly that. It is test 3 with the start moved further up, so that all the rows it needs lie above the stock bottom edge. If we are right, the frame is whole: **no black bar, no strip, and it may not stutter at all**.

**Set the camera to 24p (NTSC) or 25p (PAL).** The tests only change the full-frame 4K 24p/25p mode. At 30p the camera uses a different mode and nothing happens.

Allow about 15 minutes. You need the A7 III on firmware 4.04, a charged battery, a memory card, and its USB data cable.

**How to undo it.** The `putback` step, or taking the battery out for ten seconds, puts the camera back to stock. The power switch alone is **not** enough.

## The steps used

| Step | Launcher | What it does |
| --- | --- | --- |
| dump | `open_gate_dump` | Read-only. Saves the camera's memory facts and the timing of the last frame. |
| test 6 | `open_gate_test6` | **New.** Test 3 (92 more rows, stock line speed) with the first row moved up by all 92 rows. |
| no restart | `open_gate_norestart` | One bit. The camera's check keeps retrying but never restarts the camera. |
| put back | `open_gate_putback` | Puts the 4.04 bytes back and clears the switch. |

**Always run `no restart` right after the test step.** Without it the camera restarts itself when something is off, and the test is gone before the dump. **Do not use `open_gate_nocheck`.**

Windows launchers are `windows/<name>.cmd`. On macOS, type `bash ` (with a trailing space), drag `macos/<name>.command` into Terminal, and press Return. Every step asks for the firmware version (type `4.04`). Every step except dump also asks you to type `YES`.

## Before you start

1. Download the repo again as a ZIP and extract all of it to a new folder. Run `setup` once for that folder, then `selftest`. It must end with `0 failed` (twice).
2. On the camera: **USB Connection: Mass Storage**, **File Format: XAVC S 4K**, **Record Setting: 24p 60M** (25p on a PAL camera; **not 30p**), **APS-C/Super 35mm: Off**.

## The run

1. **Battery out for ten seconds**, then back in. Turn the camera on, dial on a stills mode, plug in USB.
2. Run **test 6**, then **no restart**. Check both say `Outcome: DONE`.
3. Unplug USB. Turn the dial to **movie**. Watch for about 15 seconds and pan slowly: **smooth or stutter? black bar near the bottom or not? streaks or not?** Record about 5 seconds.
4. Leave the dial on movie. Plug in USB. Run **dump**. It should say `VERDICT READY (test 6 applied)`.
5. Turn the dial to a stills mode. Run **put back**. It must end with `VERDICT READY (stock)`.
6. **Battery out for ten seconds** to finish.

**If the camera freezes and does not respond:** take the battery out for ten seconds and tell us where it happened.

## Please send back

- The new `M3K2_…` folders in `windows/camera_private`, zipped.
- The 5-second clip at full 3840×2160 (the camera's own file, or re-saved at full size as last time). We measure the bottom rows of the frame.
- One line: smooth or stuttering, bar or no bar, streaks or not.

**Please send the zips privately, not in a public channel.** The dump copies parts of the camera's working memory and its kernel log as text. MAC addresses in the log are blanked and the processor's serial line is not copied, but we cannot promise that nothing else in there identifies the camera.

## Results the steps can print

| Line | Meaning |
| --- | --- |
| `VERDICT READY (stock)` | The camera's program is exactly 4.04 and none of the test bytes are changed. |
| `VERDICT READY (test N applied)` | That test's bytes are in place. |
| `VERDICT NOT READY …` | The kit did not find the 4.04 program where it expected it, or the bytes are partly changed. Nothing is written in that state. |
| `Refresh-loop switch: …` | What the camera's own switch for its picture check is set to. |
| `Last frame before USB: …` | The timing the dump read. It is for us. |
| `Outcome: DONE` | The step wrote its bytes and read each back. |
| `Outcome: NOT DONE …` | Nothing was written. The line says why. One test on top of another gives this: run put back first. |
| `Outcome: NOTHING TO DO` | The bytes already were what this step writes. |
| `!! UNDO INCOMPLETE` | Take the battery out for ten seconds now. |
