#!/bin/bash
cd "$(dirname "$0")" || exit 1
py=python3
if [ -x ".venv/bin/python" ]; then py=".venv/bin/python"; fi
"$py" -I -B "../windows/tools/camera_tests/K1_readonly/pmhome_check.py"
result=$?
if [ -t 0 ]; then read -r -p "Press Return to close. "; fi
exit "$result"
