#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/source_rosmaster_env.sh"

cd "${ROSMASTER_WS}"
colcon build --symlink-install "$@"
source "${ROSMASTER_WS}/install/setup.bash"
