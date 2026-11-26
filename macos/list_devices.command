#!/bin/bash
# A7 III kit 1: shows which Sony USB devices macOS and libusb can see. Sends nothing to any device.
cd "$(dirname "$0")" || exit 1
exec "$PWD/run.sh" --list
