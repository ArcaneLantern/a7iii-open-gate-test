#!/bin/bash
# A7 III (firmware 4.04) kit 2, step test4: TEST 4: a quarter of the extra height recorded squeezed into the stock 4K file (run it only if test 3 restarts the camera).
# Changes the camera's RAM until a restart, a battery pull or open_gate_putback.command. Stretch the clip vertically by 1.046 to see it right.
# Camera: USB Connection = Mass Storage, dial on a stills mode (P/A/S/M), connected. See K2_TEST.md.
cd "$(dirname "$0")" || exit 1
read -r -p "Firmware version shown in the camera's menu (Setup, Version), e.g. 4.04: " FWV
echo "The results go to windows/camera_private (newest M3K2 folder ending in _test4). Zip that folder and send it back."
M3_SCRIPT=K2_open_gate/m3og.py exec /bin/bash "$PWD/run.sh" test4 --go --firmware-shown "$FWV" "$@"
