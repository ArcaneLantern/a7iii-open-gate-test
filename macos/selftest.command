#!/bin/bash
# A7 III kits 1 and 2: checks both kits against a simulated camera and lists exactly what the real runs would send.
# No camera needed; nothing is sent.
cd "$(dirname "$0")" || exit 1
PY="$PWD/.venv/bin/python"
K1="$PWD/../windows/tools/camera_tests/K1_readonly/m3_check.py"
K2="$PWD/../windows/tools/camera_tests/K2_open_gate/m3og.py"
if [ ! -x "$PY" ]; then echo "Python environment missing: run setup.command first."; read -r -p "Press Return to close. "; exit 1; fi
"$PY" -I -B "$K1" --selftest
echo
"$PY" -I -B "$K2" --selftest
echo
M3_SCRIPT=K2_open_gate/m3og.py exec /bin/bash "$PWD/run.sh" test2 --dry-run
