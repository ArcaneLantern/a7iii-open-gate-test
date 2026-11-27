#!/bin/bash
# A7 III (firmware 4.04) kit 2, step norestart: NO RESTART: the camera's picture check keeps retrying but never restarts the camera (one bit). Run it after a test step.
# Changes the camera's RAM until a restart, a battery pull or open_gate_putback.command.
# Camera: USB Connection = Mass Storage, dial on a stills mode (P/A/S/M), connected. See K2_TEST.md.
cd "$(dirname "$0")" || exit 1
read -r -p "Firmware version shown in the camera's menu (Setup, Version), e.g. 4.04: " FWV
echo "The results go to windows/camera_private (newest M3K2 folder ending in _norestart). Zip that folder and send it back."
M3_SCRIPT=K2_open_gate/m3og.py exec /bin/bash "$PWD/run.sh" norestart --go --firmware-shown "$FWV" "$@"
