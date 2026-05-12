#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/source_rosmaster_env.sh"

cd "${ROSMASTER_WS}"
ros2 launch launchers all_nodes.launch "$@"
