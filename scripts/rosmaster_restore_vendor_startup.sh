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
echo "This restores the Yahboom app/hotspot/display startup paths captured during inspection."

run "mkdir -p /home/jetson/.config/autostart"
run "if [ -f /home/jetson/.config/autostart.disabled/bash.desktop ]; then mv /home/jetson/.config/autostart.disabled/bash.desktop /home/jetson/.config/autostart/bash.desktop; fi"
run "sudo nmcli connection modify ROSMASTER connection.autoconnect yes || true"
run "sudo systemctl enable --now yahboom_oled.service || true"

echo "Done. Use --apply on the ROSMASTER Jetson to make changes."
