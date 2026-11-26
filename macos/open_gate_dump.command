#!/bin/bash
# A7 III (firmware 4.04) kit 2, step dump: read-only debug dump (facts, kernel log, where av-cam is, the design's bytes, sensor and front-end tables).
# Writes nothing to the camera's memory. The helper library is written to the service partition, loaded once and deleted again.
# Camera: USB Connection = Mass Storage, dial on a stills mode (P/A/S/M), connected. See K2_TEST.md.
cd "$(dirname "$0")" || exit 1
read -r -p "Firmware version shown in the camera's menu (Setup, Version), e.g. 4.04: " FWV
echo "The results go to windows/camera_private (newest M3K2 folder ending in _dump). Zip that folder and send it back."
M3_SCRIPT=K2_open_gate/m3og.py exec /bin/bash "$PWD/run.sh" dump --go --firmware-shown "$FWV" "$@"
