#!/usr/bin/env bash
set -eo pipefail

echo "[init_sensors] ROSMASTER AI Formula sensor init"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/source_rosmaster_env.sh"

pkill -f "/home/jetson/Rosmaster/rosmaster/rosmaster_main.py" 2>/dev/null || true

if command -v sudo >/dev/null 2>&1; then
  sudo udevadm trigger || true
else
  udevadm trigger || true
fi

sleep 1

if [[ ! -e /dev/myserial ]]; then
  echo "[init_sensors] ERROR: /dev/myserial is missing. Check serial.rules and the CH340 controller." >&2
  exit 1
fi

if [[ ! -r /dev/myserial || ! -w /dev/myserial ]]; then
  echo "[init_sensors] ERROR: /dev/myserial exists but is not readable/writable by this user." >&2
  ls -l /dev/myserial >&2
  exit 1
fi

ros2 pkg prefix yahboomcar_base_node >/dev/null
ros2 pkg prefix yahboomcar_description >/dev/null

echo "[init_sensors] OK: /dev/myserial and ROSMASTER base packages are available."
