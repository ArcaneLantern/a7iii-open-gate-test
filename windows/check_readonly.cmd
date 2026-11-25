@echo off
rem A7 III (firmware 4.04) kit 1: read-only service-mode check. Confirms the camera runs the 4.04 software this work is based on.
rem READ-ONLY: nothing in the camera's memory, settings or files is changed. Extra options are passed on, e.g.  --dry-run  --selftest
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing: run setup.cmd first.
  pause
  exit /b 1
)
set /p FWV=Firmware version shown in the camera's menu (Setup, Version), e.g. 4.04:
".venv\Scripts\python.exe" -I -B "tools\camera_tests\K1_readonly\m3_check.py" --go --firmware-shown %FWV% %*
echo.
echo The results are in windows\camera_private (newest folder). Zip that folder and send it back.
pause
