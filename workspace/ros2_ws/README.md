# ROSMASTER AI Formula ROS 2 Workspace

This is the deployment-shaped ROS 2 workspace for the ROSMASTER robot.

Expected robot-side workflow:

```bash
cd ~/workspace/ros2_ws/src/aiformula/launchers/shellscript
./init_sensors.sh
./build_ws.sh
./launch_all_nodes.sh
```

The `launchers` package is intentionally small. It preserves the AI Formula launch entrypoint while routing hardware-specific work through ROSMASTER adapter packages.

The shell wrappers source `/opt/ros/humble/setup.bash`, the Yahboom workspace, and this workspace's `install/setup.bash` internally. For an interactive shell, source `source_rosmaster_env.sh`.

RViz is on by default. Use `./launch_all_nodes.sh use_rviz:=false` for headless SSH runs.

Current joystick mapping:

- Hold `R2` as the deadman.
- Left-stick vertical publishes differential-drive forward/back motion.
- Right-stick horizontal publishes differential-drive yaw.
- Front steering is locked at neutral by the adapter.
- Default `V max` is `4.0`.
- `/motor_encoders` publishes the four raw Rosmaster encoder counters. On this robot channels 2 and 4 are the rear drive motors.

Run a short live check with:

```bash
cd ~/workspace/ros2_ws/src/aiformula/launchers/shellscript
./simple_path_check.sh
```
