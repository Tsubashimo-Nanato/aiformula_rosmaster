#!/usr/bin/env bash
set -euo pipefail

mode="${1:---dry-run}"

if [[ "$mode" != "--dry-run" && "$mode" != "--apply" ]]; then
  echo "Usage: $0 [--dry-run|--apply]" >&2
  exit 2
fi

run() {
  echo "+ $*"
  if [[ "$mode" == "--apply" ]]; then
    bash -lc "$*"
  fi
}

echo "Mode: $mode"
echo "This disables Yahboom app/hotspot/display startup for ROSMASTER AI Formula testing."

run "pkill -f '/home/jetson/Rosmaster/rosmaster/rosmaster_main.py' || true"
run "mkdir -p /home/jetson/.config/autostart.disabled"
run "if [ -f /home/jetson/.config/autostart/bash.desktop ]; then mv /home/jetson/.config/autostart/bash.desktop /home/jetson/.config/autostart.disabled/bash.desktop; fi"
run "sudo nmcli connection modify ROSMASTER connection.autoconnect no || true"
run "sudo nmcli connection down ROSMASTER || true"
run "sudo systemctl disable --now yahboom_oled.service || true"

echo "Done. Use --apply on the ROSMASTER Jetson to make changes."
