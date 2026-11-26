@echo off
rem A7 III (firmware 4.04) kit 2, step dump: read-only debug dump (facts, kernel log, where av-cam is, the design's bytes, sensor and front-end tables).
rem Writes nothing to the camera's memory. The helper library is written to the service partition, loaded once and deleted again.
rem Camera: USB Connection = Mass Storage, dial on a stills mode (P/A/S/M), connected. See K2_TEST.md.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing: run setup.cmd first.
  pause
  exit /b 1
)
set /p FWV=Firmware version shown in the camera's menu (Setup, Version), e.g. 4.04: 
".venv\Scripts\python.exe" -I -B "tools\camera_tests\K2_open_gate\m3og.py" dump --go --firmware-shown %FWV% %*
echo.
echo The results are in windows\camera_private (newest M3K2 folder ending in _dump). Zip that folder and send it back.
pause
