#!/bin/bash
# A7 III (firmware 4.04) kit 2, step test1: TEST 1: the 4K 24p/25p full-frame mode reads the whole sensor height (7 bytes of RAM).
# Changes the camera's RAM until a battery pull or open_gate_putback.command. The recorded 16:9 picture shifts to the top band of the sensor.
# Camera: USB Connection = Mass Storage, dial on a stills mode (P/A/S/M), connected. See K2_TEST.md.
cd "$(dirname "$0")" || exit 1
read -r -p "Firmware version shown in the camera's menu (Setup, Version), e.g. 4.04: " FWV
echo "The results go to windows/camera_private (newest M3K2 folder ending in _test1). Zip that folder and send it back."
M3_SCRIPT=K2_open_gate/m3og.py exec /bin/bash "$PWD/run.sh" test1 --go --firmware-shown "$FWV" "$@"
