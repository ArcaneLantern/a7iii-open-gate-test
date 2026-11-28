# A7 III kit 2 v14: two new tests

**If you ran kit 2 v13:** thank you. Both tests froze again, and that was the useful result: it ruled out the table those tests changed. The dumps and your clip, read together with the earlier ones, point somewhere else.

**What they show.** The camera does receive the whole taller frame. Your frozen clip is a complete frame with no noise at the bottom. The freeze comes from timing: part of the camera's front end is told to begin the next frame while the current one is still arriving, about 1 ms too early. In the stock camera the frame is finished by then. In our tests it is not, and the main reason seems to be a sensor setting all our tests have used since test 3: it makes the sensor read 327 rows before the picture starts, where the stock camera reads 45.

**What is new.** Two tests with that sensor setting put right.

- **test 16** starts the picture two rows lower and uses the camera's own sensor setting: 1 row is read before the picture.
- **test 17** starts the picture higher and uses the matching setting for that: 117 rows before the picture. Its picture ends where the stock picture ends.

**Five things to get right. Please check each:**

1. **Record Setting must be 24p (NTSC) or 25p (PAL), full frame.** At 30p, or in HD, the camera uses a different mode and the tests do nothing.
2. **Check the exposure first.** The last clips were almost all white. Before each part, look at the normal movie picture and set it so that it looks right (auto ISO is fine).
3. **Take the battery out for ten seconds before each part.** It resets the camera, and the log only keeps the first lines after a start.
4. **Leave the dial on movie when you plug USB back in for the dump.**
5. **If the picture freezes again:** press record for about 3 seconds anyway, then do the dump as written.

**For each clip, please:** point the camera at something with detail from top to bottom (a bookshelf, a window, a page of text), hold still for the first 3 seconds, then move it around for the rest.

Allow about 15 minutes. You need the A7 III on firmware 4.04, a charged battery, a memory card, and its USB data cable.

**How to undo it.** Taking the battery out for ten seconds puts the camera back to stock. So does the `putback` step. The power switch alone is **not** enough.

## The steps used

| Step | Launcher | What it does |
| --- | --- | --- |
| dump | `open_gate_dump` | Read-only. Saves the camera's memory facts, the timing of the last frame and the camera's own log. |
| test 16 | `open_gate_test16` | **New.** Test 12 with the picture from sensor row 329 and the camera's own sensor setting. Also sets `no restart` and the log. |
| test 17 | `open_gate_test17` | **New.** Test 12 with the picture from sensor row 281 and the matching sensor setting. Also sets `no restart` and the log. |
| put back | `open_gate_putback` | Puts the 4.04 bytes back and clears the switches. Not needed in this run: the battery does it. |

**Do not use `open_gate_nocheck` or `open_gate_test10`.** Tests 16 and 17 only go on a camera that is back to stock: one will not go on top of the other.

Windows launchers are `windows/<name>.cmd`. On macOS, type `bash ` (with a trailing space), drag `macos/<name>.command` into Terminal, and press Return. Every step asks for the firmware version (type `4.04`). Every step except dump also asks you to type `YES`.

## Before you start

1. Download the repo again as a ZIP and extract all of it to a new folder. Run `setup` once for that folder, then `selftest`. It must end with `0 failed`.
2. On the camera: **USB Connection: Mass Storage**, **File Format: XAVC S 4K**, **Record Setting: 24p 60M** (25p on a PAL camera), **APS-C/Super 35mm: Off**.

## The run

### Part 1: test 16

1. **Battery out for ten seconds**, then back in. Turn the camera on. Turn the dial to movie, check the picture is exposed normally, then turn it to a stills mode and plug in USB.
2. Run **test 16**. Check it says `Outcome: DONE`.
3. Unplug USB. Turn the dial to **movie**. Watch for about 15 seconds:
   - does the picture keep moving, or does it stand still;
   - smooth or stutter;
   - is the bottom edge clean, or is there a black or noisy band;
   - any fine coloured stripes, or a step down the middle.
4. Record about 6 seconds: still on something with detail, then moving. If the picture stands still, record about 3 seconds anyway.
5. Leave the dial on movie. Plug in USB. Run **dump**. It should say `VERDICT READY (test 16 applied)`.

### Part 2: test 17

6. **Battery out for ten seconds**, then back in. Turn the camera on, check the exposure in movie as in step 1, dial on a stills mode, plug in USB.
7. Run **test 17**. Check it says `Outcome: DONE`.
8. Unplug USB. Turn the dial to **movie**. Watch and record as in steps 3 and 4.
9. Leave the dial on movie. Plug in USB. Run **dump**. It should say `VERDICT READY (test 17 applied)`.
10. **Battery out for ten seconds** to finish.

**If the camera shows no picture or does not respond:** take the battery out for ten seconds and tell us what the screen showed. If USB still works in that state, a **dump** before the battery pull helps a lot.

## Please send back

- The new `M3K2_…` folders in `windows/camera_private`, zipped.
- Both clips at full 3840×2160 (the original files if they are small enough), named so we can tell which part each is.
- One line per part: moving or standing still, smooth or stuttering, the bottom edge, stripes or a step, anything else you saw.

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
