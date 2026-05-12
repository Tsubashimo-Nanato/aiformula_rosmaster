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

The ROSMASTER driver defaults to `suppress_buzzer:=true`. It periodically sends buzzer-off while the adapter stack is running because the live controller re-enabled the buzzer when battery voltage was about `9.7 V`, consistent with a low-voltage alarm. Charge the robot battery if the alarm returns when the stack is stopped.
