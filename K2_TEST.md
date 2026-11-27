# A7 III kit 2 v11: one new test

**If you ran kit 2 v10:** thank you, that run moved things on. With test 9 the black bar and the strip under it are gone for the first time. So the front-end stage was what caused them.

**What was still wrong.** In the test 9 clip the last 40 rows of the frame are coloured noise, and the picture stutters. The camera ran out of time: it sends the frame line by line, and at the stock line speed only 3,451 lines fit before the next frame starts. Test 9 asked for 3,518. The last rows were never written.

**What is new.**

- **test 11** is test 9 with the lines sent slightly faster (2.7 %), so the taller frame finishes when the stock one does.
- **The camera's own log is now really copied.** In v10 the kit found the log but refused to copy it, because of a check I got wrong.
- Test 10 made the picture worse and is not used any more.

**Three things to get right. Please check each:**

1. **Record Setting must be 24p (NTSC) or 25p (PAL), full frame.** At 30p, or in HD, the camera uses a different mode and the test does nothing.
2. **Take the battery out for ten seconds before each part.** It resets the camera, and the log only keeps the first lines after a start.
3. **Leave the dial on movie when you plug USB back in for the dump.**

**For each clip, please:** hold the camera still on something plain (a wall or a sheet of paper) for the first 3 seconds, then move it around for the rest. The still part shows us the picture's fine detail, the moving part shows the stutter.

Allow about 15 minutes. You need the A7 III on firmware 4.04, a charged battery, a memory card, and its USB data cable.

**How to undo it.** Taking the battery out for ten seconds puts the camera back to stock. So does the `putback` step. The power switch alone is **not** enough.

## The steps used

| Step | Launcher | What it does |
| --- | --- | --- |
| dump | `open_gate_dump` | Read-only. Saves the camera's memory facts, the timing of the last frame and the camera's own log. |
| log | `open_gate_dfelog` | One flag byte: the firmware writes its front end's status into its log. |
| test 11 | `open_gate_test11` | **New.** Test 9 with the lines sent 2.7 % faster. Also sets `no restart` and the log. |
| put back | `open_gate_putback` | Puts the 4.04 bytes back and clears the switches. Not needed in this run: the battery does it. |

**Do not use `open_gate_nocheck` or `open_gate_test10`.**

Windows launchers are `windows/<name>.cmd`. On macOS, type `bash ` (with a trailing space), drag `macos/<name>.command` into Terminal, and press Return. Every step asks for the firmware version (type `4.04`). Every step except dump also asks you to type `YES`.

## Before you start

1. Download the repo again as a ZIP and extract all of it to a new folder. Run `setup` once for that folder, then `selftest`. It must end with `0 failed`.
2. On the camera: **USB Connection: Mass Storage**, **File Format: XAVC S 4K**, **Record Setting: 24p 60M** (25p on a PAL camera), **APS-C/Super 35mm: Off**.

## The run

### Part 1: the stock camera's log

1. **Battery out for ten seconds**, then back in. Turn the camera on, dial on a stills mode, plug in USB.
2. Run **log** (`open_gate_dfelog`). Check it says `Outcome: DONE`.
3. Unplug USB. Turn the dial to **movie**. Record about 6 seconds: still on something plain, then moving.
4. Leave the dial on movie. Plug in USB. Run **dump**. It should say `VERDICT READY (stock)` and a line starting `Camera log:`.

### Part 2: test 11

5. **Battery out for ten seconds**, then back in. Turn the camera on, dial on a stills mode, plug in USB.
6. Run **test 11**. Check it says `Outcome: DONE`.
7. Unplug USB. Turn the dial to **movie**. Watch for about 15 seconds: smooth or stutter, noise at the bottom edge or not, any picture at all. Record about 6 seconds: still on something plain, then moving.
8. Leave the dial on movie. Plug in USB. Run **dump**. It should say `VERDICT READY (test 11 applied)`. On a PAL camera it says `test 9 applied`: there the two tests are the same.
9. **Battery out for ten seconds** to finish.

**If the camera shows no picture, freezes or does not respond:** take the battery out for ten seconds and tell us what the screen showed. If USB still works in that state, a **dump** before the battery pull helps a lot.

## Please send back

- The new `M3K2_…` folders in `windows/camera_private`, zipped.
- The two clips at full 3840×2160, named so we can tell which part each is.
- One line per part: smooth or stuttering, noise at the bottom or not, anything else you saw.

**Please send the zips privately, not in a public channel.** The dump copies parts of the camera's working memory, its kernel log and the camera's own log as text. MAC addresses are blanked and the processor's serial line is not copied, but the camera's own log may name the camera or the lens by serial number. We cannot promise that nothing in there identifies the camera.

## Results the steps can print

| Line | Meaning |
| --- | --- |
| `VERDICT READY (stock)` | The camera's program is exactly 4.04 and none of the test bytes are changed. |
| `VERDICT READY (test N applied)` | That test's bytes are in place. |
| `VERDICT NOT READY …` | The kit did not find the 4.04 program where it expected it, or the bytes are partly changed. Nothing is written in that state. |
| `Refresh-loop switch: …` | What the camera's own switch for its picture check is set to. |
| `Front-end log switch: …` | Whether the firmware's front-end status print is on. |
| `Camera log: …` | How much of the camera's own log the dump copied, with a few of its lines. It is for us. |
| `Last frame before USB: …` | The timing the dump read. It is for us. |
| `Outcome: DONE` | The step wrote its bytes and read each back. |
| `Outcome: NOT DONE …` | Nothing was written. The line says why. One test on top of another gives this: take the battery out for ten seconds first. |
| `Outcome: NOTHING TO DO` | The bytes already were what this step writes. |
| `!! UNDO INCOMPLETE` | Take the battery out for ten seconds now. |
