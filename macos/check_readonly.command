#!/bin/bash
# A7 III (firmware 4.04) kit 1 v2: service-mode file check. Confirms the camera runs the 4.04 software this work is based on.
# No camera file, setting or memory is written. For the length of the run the camera's service work area is mounted
# (Sony's own service step); it is unmounted and its folder removed again at the end. Extra options are passed on.
cd "$(dirname "$0")" || exit 1
read -r -p "Firmware version shown in the camera's menu (Setup, Version), e.g. 4.04: " FWV
echo "The results go to windows/camera_private (newest M3K1v2 folder). Zip that folder and send it back."
exec "$PWD/run.sh" --go --firmware-shown "$FWV" "$@"
