#!/bin/bash
# A7 III (firmware 4.04) kit 1: read-only service-mode check. Confirms the camera runs the 4.04 software this work is based on.
# READ-ONLY: nothing in the camera's memory, settings or files is changed. Extra options are passed on.
cd "$(dirname "$0")" || exit 1
read -r -p "Firmware version shown in the camera's menu (Setup, Version), e.g. 4.04: " FWV
echo "The results go to windows/camera_private (newest folder). Zip that folder and send it back."
exec "$PWD/run.sh" --go --firmware-shown "$FWV" "$@"
