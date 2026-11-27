# A7 III kit 2 v6: one short test (NTSC cameras)

**If you ran kit 2 v5:** thank you. The three dumps with the dial on movie worked. They showed that the camera's timing signal does **not** move when the picture gets taller, which rules out what we thought was wrong. Your note that test 2 moved the top strip of the picture to the bottom was the other useful clue.

**What this run is for.** Tests 2 and 4 change two things at once: how many lines the camera counts per frame, and how fast it counts them. This run changes only the first. The new test 3 adds a small amount of height (92 rows, a squeeze of 1.03, hard to see by eye) and leaves the line speed stock. If the picture is smooth, we know the line speed is what the camera cannot take, and where to go next.

**This run is for cameras set to NTSC (24p).** On a PAL camera there is no room to add lines without changing the speed, so the result would not answer the question. If your camera is PAL, please wait for the next kit.

Allow about 15 minutes. You need the A7 III on firmware 4.04, a charged battery, a memory card, and its USB data cable.

**How to undo it.** The `putback` step, or taking the battery out for ten seconds, puts the camera back to stock. The power switch alone is **not** enough.

## The steps used

| Step | Launcher | What it does |
| --- | --- | --- |
| dump | `open_gate_dump` | Read-only. Saves the camera's memory facts and the timing of the last frame. |
| test 3 | `open_gate_test3` | 92 more rows, stock line speed. **New in v6**: the old test 3 is gone. |
| no restart | `open_gate_norestart` | One bit. The camera's check keeps retrying but never restarts the camera. |
| put back | `open_gate_putback` | Puts the 4.04 bytes back and clears the switch. |

**Do not use `open_gate_nocheck`.** With the full-height test it froze a camera hard (battery pull needed).

Windows launchers are `windows/<name>.cmd`. On macOS, type `bash ` (with a trailing space), drag `macos/<name>.command` into Terminal, and press Return. Every step asks for the firmware version (type `4.04`). Every step except dump also asks you to type `YES`.

## Before you start

1. Download the repo again as a ZIP and extract all of it to a new folder. Run `setup` once for that folder, then `selftest`. It must end with `0 failed` (twice).
2. On the camera: **USB Connection: Mass Storage**, **File Format: XAVC S 4K**, **Record Setting: 24p 60M**, **APS-C/Super 35mm: Off**.

## The run

1. **Battery out for ten seconds**, then back in. Turn the camera on, dial on a stills mode, plug in USB.
2. Run **test 3**, then **no restart**. Check both say `Outcome: DONE`.
3. Unplug USB. Turn the dial to **movie**. Watch for about 15 seconds and pan the camera slowly. The question is simple: **is the picture smooth like stock, or does it stutter like tests 2 and 4 did?** Record about 5 seconds.
4. Leave the dial on movie. Plug in USB. Run **dump**. It should say `VERDICT READY (test 3 applied)`.
5. Turn the dial to a stills mode. Run **put back**. It must end with `VERDICT READY (stock)`.
6. **Battery out for ten seconds** to finish.

**If the camera freezes and does not respond:** take the battery out for ten seconds and tell us where it happened.

## Please send back

- The new `M3K2_…` folders in `windows/camera_private`, zipped.
- One line: smooth or stuttering, and anything else you saw (a moved strip, wrong brightness).
- Whether the 5-second clip plays back smoothly on a computer.

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
