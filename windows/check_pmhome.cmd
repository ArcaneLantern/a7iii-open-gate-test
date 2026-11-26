@echo off
setlocal
cd /d "%~dp0"
set "script=tools\camera_tests\K1_readonly\pmhome_check.py"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -I -B "%script%"
) else (
  where.exe py.exe >nul 2>&1
  if errorlevel 1 (
    python.exe -I -B "%script%"
  ) else (
    py.exe -3 -I -B "%script%"
  )
)
set "result=%errorlevel%"
pause
exit /b %result%
