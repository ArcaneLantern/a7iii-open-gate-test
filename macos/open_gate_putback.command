#!/bin/bash
# A7 III (firmware 4.04) kit 2, step putback: PUT BACK: the 4.04 bytes again wherever test 1 or test 2 changed them.
# A battery pull (ten seconds) does the same.
# Camera: USB Connection = Mass Storage, dial on a stills mode (P/A/S/M), connected. See K2_TEST.md.
cd "$(dirname "$0")" || exit 1
read -r -p "Firmware version shown in the camera's menu (Setup, Version), e.g. 4.04: " FWV
echo "The results go to windows/camera_private (newest M3K2 folder ending in _putback). Zip that folder and send it back."
M3_SCRIPT=K2_open_gate/m3og.py exec /bin/bash "$PWD/run.sh" putback --go --firmware-shown "$FWV" "$@"
