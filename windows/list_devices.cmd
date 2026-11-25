@echo off
rem A7 III kit 1: shows which Sony USB devices Windows and libusb can see (to check the Zadig step). Sends nothing to any device.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing: run setup.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -I -B "tools\camera_tests\K1_readonly\m3_check.py" --list
pause
