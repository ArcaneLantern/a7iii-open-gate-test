# A7 III kit 2 v7: one short test

**If you ran kit 2 v6:** thank you, and thank you for the clip. It gave us the best clue so far. Test 3 still stuttered, which cleared one suspect. The black bar and the strip of picture under it in your clip gave us the other: the camera only delivers **half** of the extra rows we ask for. After that comes black, then the top of the picture again. A frame that is cut short like that is what makes the camera stutter.

**What this run is for.** The camera keeps its own note of the picture height for this mode, and every test so far has left that note stock. The new **test 5** is test 3 with that note raised to match. If that is what holds the picture back, the black bar and the strip disappear.

Either TV system works. An NTSC (24p) camera gives the cleanest answer.

Allow about 15 minutes. You need the A7 III on firmware 4.04, a charged battery, a memory card, and its USB data cable.

**How to undo it.** The `putback` step, or taking the battery out for ten seconds, puts the camera back to stock. The power switch alone is **not** enough.

## The steps used

| Step | Launcher | What it does |
| --- | --- | --- |
| dump | `open_gate_dump` | Read-only. Saves the camera's memory facts and the timing of the last frame. |
| test 5 | `open_gate_test5` | **New.** Test 3 (92 more rows, stock line speed) plus the camera's own picture-height note. |
| no restart | `open_gate_norestart` | One bit. The camera's check keeps retrying but never restarts the camera. |
| put back | `open_gate_putback` | Puts the 4.04 bytes back and clears the switch. |

**Do not use `open_gate_nocheck`.** With the full-height test it froze a camera hard.

Windows launchers are `windows/<name>.cmd`. On macOS, type `bash ` (with a trailing space), drag `macos/<name>.command` into Terminal, and press Return. Every step asks for the firmware version (type `4.04`). Every step except dump also asks you to type `YES`.

## Before you start

1. Download the repo again as a ZIP and extract all of it to a new folder. Run `setup` once for that folder, then `selftest`. It must end with `0 failed` (twice).
2. On the camera: **USB Connection: Mass Storage**, **File Format: XAVC S 4K**, **Record Setting: 24p 60M** (25p on a PAL camera), **APS-C/Super 35mm: Off**.

## The run

1. **Battery out for ten seconds**, then back in. Turn the camera on, dial on a stills mode, plug in USB.
2. Run **test 5**, then **no restart**. Check both say `Outcome: DONE`.
3. Unplug USB. Turn the dial to **movie**. Watch for about 15 seconds and pan slowly. Two things to look for: **is it smooth or does it stutter**, and **is there a black bar near the bottom edge** as before? Record about 5 seconds, with something bright in the frame if you can.
4. Leave the dial on movie. Plug in USB. Run **dump**. It should say `VERDICT READY (test 5 applied)`.
5. Turn the dial to a stills mode. Run **put back**. It must end with `VERDICT READY (stock)`.
6. **Battery out for ten seconds** to finish.

**If the camera freezes and does not respond:** take the battery out for ten seconds and tell us where it happened.

Because this test changes the camera's own idea of the picture height, focus areas and exposure may behave differently while it is applied. That is expected and goes away with put back.

## Please send back

- The new `M3K2_…` folders in `windows/camera_private`, zipped.
- The 5-second clip **as the camera recorded it** (or re-saved at full 3840×2160). We measure the bottom rows of the frame, so a phone video of the screen does not work for this one.
- One line: smooth or stuttering, bar or no bar, and anything else you saw.

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
