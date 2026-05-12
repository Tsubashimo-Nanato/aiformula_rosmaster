# AI Formula ROSMASTER Adapter

This repository contains the minimal ROS 2 adapter workspace for using a Yahboom ROSMASTER robot as a development and testing platform for the AI Formula/Sophia robot stack.

The working deployment shape is:

```text
workspace/ros2_ws/src/aiformula
```

On the ROSMASTER Jetson, the workspace was deployed to:

```text
/home/jetson/workspace/ros2_ws
```

## Robot-Side Workflow

```bash
cd /home/jetson/workspace/ros2_ws/src/aiformula/launchers/shellscript
./init_sensors.sh
./launch_all_nodes.sh
```

The wrapper sources ROS 2 Humble, the Yahboom workspace, and `/home/jetson/workspace/ros2_ws/install/setup.bash` before launching. For manual shells, use:

```bash
source /home/jetson/workspace/ros2_ws/src/aiformula/launchers/shellscript/source_rosmaster_env.sh
```

## Packages

- `launchers`: AI Formula-style launch entrypoint.
- `rosmaster_aiformula_bridge`: ROSMASTER hardware driver and AI Formula topic compatibility bridge.
- `rosmaster_aiformula_bringup`: ROSMASTER base bringup composed for AI Formula testing.

## Notes

- Large local mirrors and proprietary snapshots are intentionally ignored by Git.
- The adapter uses `Rosmaster_Lib` for the ROSMASTER controller and keeps Sophia-facing topics under `/aiformula_*`.
- The live ROSMASTER is treated as an R2-style platform: front steering exists, but the current adapter locks the front steering servos at neutral and drives rear motor channels 2 and 4 with differential-drive `linear.x`/`angular.z` semantics.
- USB gamepad control is enabled by default. Hold `R2`, use left-stick vertical for forward/back, and use right-stick horizontal for differential yaw.
- Default `V max` is `4.0`.
- RViz is on by default. Use `./launch_all_nodes.sh use_rviz:=false` for headless SSH runs.
- Chinese overview: `README.zh-CN.md`.
- See `codex/live_rosmaster_deployment_log.md` for the latest live robot build and test record.
