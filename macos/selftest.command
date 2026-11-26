#!/bin/bash
# A7 III kit 1: checks the kit against a simulated camera and lists exactly what the real run would send.
# No camera needed; nothing is sent.
cd "$(dirname "$0")" || exit 1
PY="$PWD/.venv/bin/python"
SCRIPT="$PWD/../windows/tools/camera_tests/K1_readonly/m3_check.py"
if [ ! -x "$PY" ]; then echo "Python environment missing: run setup.command first."; read -r -p "Press Return to close. "; exit 1; fi
"$PY" -I -B "$SCRIPT" --selftest
echo
exec "$PWD/run.sh" --dry-run
