#!/bin/bash
# A7 III (firmware 4.04) kit 2, step dfelog: FRONT-END LOG (v10): switches on the firmware's own status print for its front end (four bits of one byte). The next dump copies the camera's log.
# Changes the camera's RAM until a restart, a battery pull or open_gate_putback.command.
# Camera: USB Connection = Mass Storage, dial on a stills mode (P/A/S/M), connected. See K2_TEST.md.
cd "$(dirname "$0")" || exit 1
read -r -p "Firmware version shown in the camera's menu (Setup, Version), e.g. 4.04: " FWV
echo "The results go to windows/camera_private (newest M3K2 folder ending in _dfelog). Zip that folder and send it back."
M3_SCRIPT=K2_open_gate/m3og.py exec /bin/bash "$PWD/run.sh" dfelog --go --firmware-shown "$FWV" "$@"
