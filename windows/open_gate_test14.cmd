@echo off
rem A7 III (firmware 4.04) kit 2, step test14: TEST 14 (v13): test 12 plus the front end's geometry table at the taller height. It also sets no-restart and the front-end log itself. Does the picture keep moving?
rem Changes the camera's RAM until a restart, a battery pull or open_gate_putback.cmd. Stretch the clip vertically by 1.027 to see it right.
rem Camera: USB Connection = Mass Storage, dial on a stills mode (P/A/S/M), connected. See K2_TEST.md.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing: run setup.cmd first.
  pause
  exit /b 1
)
set /p FWV=Firmware version shown in the camera's menu (Setup, Version), e.g. 4.04: 
".venv\Scripts\python.exe" -I -B "tools\camera_tests\K2_open_gate\m3og.py" test14 --go --firmware-shown %FWV% %*
echo.
echo The results are in windows\camera_private (newest M3K2 folder ending in _test14). Zip that folder and send it back.
pause
