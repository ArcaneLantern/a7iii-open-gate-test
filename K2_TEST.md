# A7 III kit 2 v9: two short tests

**If you ran kit 2 v8:** thank you. Test 6 recorded exactly the same frame as tests 3 and 5: the picture stops at the same row, then the black bar, then the thin strip. So where the sensor starts reading makes no difference, and that idea is closed too.

**What the four clips say together.** The camera delivers the stock number of lines plus exactly half of what we add, every time. That fits a simple picture: the line count is kept in two places, and we have only been changing one of them. There are two candidates for the pair, and we always changed both by the same amount, so the clips cannot tell which pair it is. The two new tests each change one candidate by twice as much:

- **test 7** doubles the change to the camera's own line count;
- **test 8** doubles the change to the sensor's row count.

If either idea is right, one of the two gives a whole frame: **no black bar, no strip**.

**Three things that have gone wrong in earlier runs. Please check each:**

1. **Record Setting must be 24p (NTSC) or 25p (PAL), full frame.** At 30p, or in HD, the camera uses a different mode and the tests do nothing.
2. **Run `no restart` straight after every test step.** Without it the camera restarts itself in movie mode and the test is gone.
3. **Run `put back` between the two tests.** One test on top of another is refused.

Allow about 25 minutes. You need the A7 III on firmware 4.04, a charged battery, a memory card, and its USB data cable.

**How to undo it.** The `putback` step, or taking the battery out for ten seconds, puts the camera back to stock. The power switch alone is **not** enough.

## The steps used

| Step | Launcher | What it does |
| --- | --- | --- |
| dump | `open_gate_dump` | Read-only. Saves the camera's memory facts and the timing of the last frame. |
| test 7 | `open_gate_test7` | **New.** Test 3 with the camera's line count raised twice as far. |
| test 8 | `open_gate_test8` | **New.** Test 3 with the sensor's row count raised twice as far. |
| no restart | `open_gate_norestart` | One bit. The camera's check keeps retrying but never restarts the camera. |
| put back | `open_gate_putback` | Puts the 4.04 bytes back and clears the switch. |

**Do not use `open_gate_nocheck`.**

Windows launchers are `windows/<name>.cmd`. On macOS, type `bash ` (with a trailing space), drag `macos/<name>.command` into Terminal, and press Return. Every step asks for the firmware version (type `4.04`). Every step except dump also asks you to type `YES`.

## Before you start

1. Download the repo again as a ZIP and extract all of it to a new folder. Run `setup` once for that folder, then `selftest`. It must end with `0 failed` (twice).
2. On the camera: **USB Connection: Mass Storage**, **File Format: XAVC S 4K**, **Record Setting: 24p 60M** (25p on a PAL camera), **APS-C/Super 35mm: Off**.

## The run

### Test 7

1. **Battery out for ten seconds**, then back in. Turn the camera on, dial on a stills mode, plug in USB.
2. Run **test 7**, then **no restart**. Check both say `Outcome: DONE`.
3. Unplug USB. Turn the dial to **movie**. Watch for about 15 seconds: smooth or stutter, black bar near the bottom or not. Record about 5 seconds.
4. Leave the dial on movie. Plug in USB. Run **dump**. It should say `VERDICT READY (test 7 applied)`.
5. Turn the dial to a stills mode. Run **put back**. It must end with `VERDICT READY (stock)`.

### Test 8

6. Run **test 8**, then **no restart**. Check both say `Outcome: DONE`.
7. Unplug USB. Turn the dial to **movie**. Watch for about 15 seconds as before. Record about 5 seconds.
8. Leave the dial on movie. Plug in USB. Run **dump**. It should say `VERDICT READY (test 8 applied)`.
9. Turn the dial to a stills mode. Run **put back**.
10. **Battery out for ten seconds** to finish.

**If the camera freezes and does not respond:** take the battery out for ten seconds, tell us where it happened, and go on with the other test.

## Please send back

- The new `M3K2_…` folders in `windows/camera_private`, zipped.
- Both 5-second clips at full 3840×2160, named so we can tell which test each is.
- One line per test: smooth or stuttering, bar or no bar.

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
