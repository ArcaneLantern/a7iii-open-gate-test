@echo off
rem A7 III (firmware 4.04) kit 1 v2: service-mode file check. Confirms the camera runs the 4.04 software this work is based on.
rem No camera file, setting or memory is written. For the length of the run the camera's service work area is mounted
rem (Sony's own service step); it is unmounted and its folder removed again at the end. Extra options are passed on, e.g.  --dry-run  --selftest
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing: run setup.cmd first.
  pause
  exit /b 1
)
set /p FWV=Firmware version shown in the camera's menu (Setup, Version), e.g. 4.04:
".venv\Scripts\python.exe" -I -B "tools\camera_tests\K1_readonly\m3_check.py" --go --firmware-shown %FWV% %*
echo.
echo The results are in windows\camera_private (newest M3K1v2 folder). Zip that folder and send it back.
pause
