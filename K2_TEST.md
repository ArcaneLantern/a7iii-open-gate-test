# A7 III kit 2 v10: the front end

**If you ran kit 2 v9:** thank you. Tests 7 and 8 both recorded the same frame as test 3: the picture stops at the same row, then the black bar, then the thin strip. So neither of the two counts they changed is the cause.

**What we found since.** Between the sensor and the camera's main processor sits a front-end stage with its own settings for each video mode. For 4K it still describes the stock frame, and none of the eight tests ever changed it. The two new tests do. There is also a new log step: the camera's firmware can write down what its front end is doing, and the dump now copies that log out.

**Three things to get right. Please check each:**

1. **Record Setting must be 24p (NTSC) or 25p (PAL), full frame.** At 30p, or in HD, the camera uses a different mode and the tests do nothing.
2. **Take the battery out for ten seconds before each part.** It resets the camera, and the log only keeps the first lines after a start.
3. **Leave the dial on movie when you plug USB back in for the dump.**

You no longer run `no restart` yourself: tests 9 and 10 set it.

**If you can:** put the camera on a tripod or a table, pointed at something with clear detail, and do not move it between the three parts. Then the three clips show the same scene and we can compare how much of it each one sees.

Allow about 25 minutes. You need the A7 III on firmware 4.04, a charged battery, a memory card, and its USB data cable.

**How to undo it.** Taking the battery out for ten seconds puts the camera back to stock. So does the `putback` step. The power switch alone is **not** enough.

## The steps used

| Step | Launcher | What it does |
| --- | --- | --- |
| dump | `open_gate_dump` | Read-only. Saves the camera's memory facts, the timing of the last frame and, new, the camera's own log. |
| log | `open_gate_dfelog` | **New.** One flag byte: the firmware writes its front end's status into its log. |
| test 9 | `open_gate_test9` | **New.** Test 3 plus the front end's own line counts. Also sets `no restart` and the log. |
| test 10 | `open_gate_test10` | **New.** Test 9 plus the front end's picture-size table. Also sets `no restart` and the log. |
| put back | `open_gate_putback` | Puts the 4.04 bytes back and clears the switches. Not needed in this run: the battery does it. |

**Do not use `open_gate_nocheck`.**

Windows launchers are `windows/<name>.cmd`. On macOS, type `bash ` (with a trailing space), drag `macos/<name>.command` into Terminal, and press Return. Every step asks for the firmware version (type `4.04`). Every step except dump also asks you to type `YES`.

## Before you start

1. Download the repo again as a ZIP and extract all of it to a new folder. Run `setup` once for that folder, then `selftest`. It must end with `0 failed`.
2. On the camera: **USB Connection: Mass Storage**, **File Format: XAVC S 4K**, **Record Setting: 24p 60M** (25p on a PAL camera), **APS-C/Super 35mm: Off**.

## The run

### Part 1: the stock camera's log

1. **Battery out for ten seconds**, then back in. Turn the camera on, dial on a stills mode, plug in USB.
2. Run **log** (`open_gate_dfelog`). Check it says `Outcome: DONE`.
3. Unplug USB. Turn the dial to **movie**. Record about 5 seconds.
4. Leave the dial on movie. Plug in USB. Run **dump**. It should say `VERDICT READY (stock)`.

### Part 2: test 9

5. **Battery out for ten seconds**, then back in. Turn the camera on, dial on a stills mode, plug in USB.
6. Run **test 9**. Check it says `Outcome: DONE`.
7. Unplug USB. Turn the dial to **movie**. Watch for about 15 seconds: smooth or stutter, black bar near the bottom or not, any picture at all. Record about 5 seconds.
8. Leave the dial on movie. Plug in USB. Run **dump**. It should say `VERDICT READY (test 9 applied)`.

### Part 3: test 10

9. **Battery out for ten seconds**, then back in. Turn the camera on, dial on a stills mode, plug in USB.
10. Run **test 10**. Check it says `Outcome: DONE`.
11. Unplug USB. Turn the dial to **movie**. Watch for about 15 seconds as before. Record about 5 seconds.
12. Leave the dial on movie. Plug in USB. Run **dump**. It should say `VERDICT READY (test 10 applied)`.
13. **Battery out for ten seconds** to finish.

**If the camera shows no picture, freezes or does not respond:** take the battery out for ten seconds, tell us in which part it happened and what the screen showed, and go on with the next part. If USB still works in that state, a **dump** before the battery pull helps a lot.

## Please send back

- The new `M3K2_…` folders in `windows/camera_private`, zipped.
- The three 5-second clips at full 3840×2160, named so we can tell which part each is.
- One line per part: smooth or stuttering, bar or no bar, anything else you saw.

**Please send the zips privately, not in a public channel.** The dump copies parts of the camera's working memory, its kernel log and, new in this version, the camera's own log as text. MAC addresses are blanked and the processor's serial line is not copied, but the camera's own log may name the camera or the lens by serial number. We cannot promise that nothing in there identifies the camera.

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
