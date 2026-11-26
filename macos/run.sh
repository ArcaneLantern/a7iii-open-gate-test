#!/bin/bash
# Shared by the .command launchers: runs the Windows kit's own script with this folder's Python.
#   run.sh <script arguments>                                   kit 1 (K1_readonly/m3_check.py)
#   M3_SCRIPT=K2_open_gate/m3og.py run.sh <script arguments>    kit 2
# macOS keeps its own mass-storage driver on the camera, and only root may take the camera over from it, so the live
# run (--go) goes through sudo. --dry-run, --selftest and --list send nothing and run without it.
cd "$(dirname "$0")" || exit 1
PY="$PWD/.venv/bin/python"
case "${M3_SCRIPT:-K1_readonly/m3_check.py}" in
  K1_readonly/m3_check.py|K2_open_gate/m3og.py) SCRIPT="$PWD/../windows/tools/camera_tests/${M3_SCRIPT:-K1_readonly/m3_check.py}" ;;
  *) echo "Unknown kit script: $M3_SCRIPT"; exit 1 ;;
esac
PRIVATE="$PWD/../windows/camera_private"
close() { echo; read -r -p "Press Return to close. "; exit "$1"; }
if [ ! -x "$PY" ]; then
  echo "Python environment missing: run setup.command first."
  close 1
fi
case " $* " in
  *" --go "*) ;;
  *) "$PY" -I -B "$SCRIPT" "$@"; close $? ;;
esac
echo "macOS asks for your password: taking the camera over from its own USB driver needs admin rights."
# The session is saved as root; the same root shell gives it back to you afterwards. `trap : INT` keeps that shell
# alive through Ctrl+C (the child still stops), so the results are given back then too.
sudo /bin/bash -c 'trap : INT; private=$1; shift; "$@"; status=$?
  [ -d "$private" ] && chown -R "$SUDO_UID:$SUDO_GID" "$private"; exit $status' run "$PRIVATE" "$PY" -I -B "$SCRIPT" "$@"
close $?
