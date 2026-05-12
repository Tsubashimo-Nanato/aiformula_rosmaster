#!/usr/bin/env bash
# Source this file, or use the wrapper scripts beside it.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROSMASTER_WS="${ROSMASTER_WS:-$(cd "${SCRIPT_DIR}/../../../.." && pwd)}"
YAHBOOM_WS="${YAHBOOM_WS:-/home/jetson/yahboomcar_ros2_ws/yahboomcar_ws}"

source /opt/ros/humble/setup.bash

if [[ -f "${YAHBOOM_WS}/install/setup.bash" ]]; then
  source "${YAHBOOM_WS}/install/setup.bash"
fi

if [[ -f "${ROSMASTER_WS}/install/setup.bash" ]]; then
  source "${ROSMASTER_WS}/install/setup.bash"
fi

export ROSMASTER_WS
export YAHBOOM_WS
