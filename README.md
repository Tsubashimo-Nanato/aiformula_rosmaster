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
cd /home/jetson/workspace/ros2_ws
source /opt/ros/humble/setup.bash
source /home/jetson/yahboomcar_ros2_ws/yahboomcar_ws/install/setup.bash
source install/setup.bash
ros2 launch launchers all_nodes.launch
```

`all_nodes.launch.py` is also available.

## Packages

- `launchers`: AI Formula-style launch entrypoint.
- `rosmaster_aiformula_bridge`: ROSMASTER hardware driver and AI Formula topic compatibility bridge.
- `rosmaster_aiformula_bringup`: ROSMASTER base bringup composed for AI Formula testing.

## Notes

- Large local mirrors and proprietary snapshots are intentionally ignored by Git.
- The adapter uses `Rosmaster_Lib` for the ROSMASTER controller and keeps Sophia-facing topics under `/aiformula_*`.
- The ROSMASTER driver defaults to `suppress_buzzer:=true`, which sends buzzer-off periodically while the adapter stack is running. This mitigates the controller low-voltage alarm; charge the robot battery if the alarm returns when the stack is stopped.
- See `codex/live_rosmaster_deployment_log.md` for the latest live robot build and test record.
