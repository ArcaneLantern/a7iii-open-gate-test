@echo off
rem A7 III kits 1 and 2: checks both kits against a simulated camera and lists exactly what the real runs would send. No camera needed; nothing is sent.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Python environment missing: run setup.cmd first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -I -B "tools\camera_tests\K1_readonly\m3_check.py" --selftest
echo.
".venv\Scripts\python.exe" -I -B "tools\camera_tests\K2_open_gate\m3og.py" --selftest
echo.
".venv\Scripts\python.exe" -I -B "tools\camera_tests\K2_open_gate\m3og.py" test2 --dry-run
pause
