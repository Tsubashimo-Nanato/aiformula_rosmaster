# ROSMASTER AI Formula ROS 2 Workspace

This is the deployment-shaped ROS 2 workspace for the ROSMASTER robot.

Expected robot-side workflow:

```bash
cd ~/workspace/ros2_ws/src/aiformula/launchers/shellscript
./init_sensors.sh
cd ~/workspace/ros2_ws
colcon build --symlink-install
source /opt/ros/humble/setup.bash
source /home/jetson/yahboomcar_ros2_ws/yahboomcar_ws/install/setup.bash
source install/setup.bash
ros2 launch launchers all_nodes.launch.py
```

The `launchers` package is intentionally small. It preserves the AI Formula launch entrypoint while routing hardware-specific work through ROSMASTER adapter packages.

`ros2 launch launchers all_nodes.launch` is the preferred command. RViz defaults to off when `DISPLAY` is unset, which avoids Qt/XCB errors over SSH.

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
