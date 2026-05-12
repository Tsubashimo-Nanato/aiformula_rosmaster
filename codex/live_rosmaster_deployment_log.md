# Live ROSMASTER Deployment Log

Date: 2026-05-13

Robot: `jetson@192.168.0.38`

## Deployed Workspace

Remote workspace:

```text
/home/jetson/workspace/ros2_ws
```

Source layout:

```text
/home/jetson/workspace/ros2_ws/src/aiformula
  launchers
  rosmaster_aiformula_bridge
  rosmaster_aiformula_bringup
```

This is a minimal adapter workspace. It does not copy Sophia perception weights or bulk ROSMASTER proprietary assets.

## Build Result

Command run on robot:

```bash
cd /home/jetson/workspace/ros2_ws
source /opt/ros/humble/setup.bash
source /home/jetson/yahboomcar_ros2_ws/yahboomcar_ws/install/setup.bash
colcon build --symlink-install --event-handlers console_direct+
```

Result:

```text
Summary: 3 packages finished
```

Packages:

- `launchers`
- `rosmaster_aiformula_bridge`
- `rosmaster_aiformula_bringup`

## Intended Runtime Commands

```bash
cd /home/jetson/workspace/ros2_ws/src/aiformula/launchers/shellscript
./init_sensors.sh
cd /home/jetson/workspace/ros2_ws
source /opt/ros/humble/setup.bash
source /home/jetson/yahboomcar_ros2_ws/yahboomcar_ws/install/setup.bash
source install/setup.bash
ros2 launch launchers all_nodes.launch
```

`all_nodes.launch.py` is also available. The extensionless-style `all_nodes.launch` XML wrapper was tested with ROS 2 launch and works.

## Nodes Started

Headless launch test with `use_rviz:=false` started:

```text
/imu_filter_madgwick
/robot_state_publisher
/rosmaster_aiformula_compat_bridge
/rosmaster_base_node
/rosmaster_driver
```

Default launch with RViz on display `:0` additionally started:

```text
/rviz2
/transform_listener_impl_*
```

RViz initialized OpenGL successfully and exited cleanly on shutdown.

## Topics Verified

Relevant topics present:

```text
/aiformula_control/game_pad/cmd_vel
/aiformula_sensing/gyro_odometry_publisher/odom
/aiformula_sensing/rear_potentiometer/yaw
/aiformula_sensing/vectornav/imu
/aiformula_sensing/vectornav/velocity_body
/cmd_vel
/imu/data
/imu/data_raw
/imu/mag
/odom_raw
/vel_raw
/voltage
```

Published a low-speed command while robot was suspended:

```bash
ros2 topic pub --once /aiformula_control/game_pad/cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.08, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

Then published zero:

```bash
ros2 topic pub --once /aiformula_control/game_pad/cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"
```

An odometry sample was received from:

```text
/aiformula_sensing/gyro_odometry_publisher/odom
```

## Direct Actuator Test

Direct `Rosmaster_Lib` test completed before launch validation:

- Opened `/dev/myserial`.
- Battery read about `10.1 V`.
- IMU acceleration/gyro responded.
- UART servo angle scan returned `[-1, -1, -1, -1, -1, -1]`, so no bus servos were detected.
- Low-speed forward, backward, lateral, and yaw commands changed encoder readings.
- A final zero-motion command was sent.

## Boot Cleanup Applied

Applied reversible boot cleanup on the live robot:

- Moved Yahboom app autostart:
  - From `/home/jetson/.config/autostart/bash.desktop`
  - To `/home/jetson/.config/autostart.disabled/bash.desktop`
- Disabled ROSMASTER hotspot autoconnect:
  - `sudo nmcli connection modify ROSMASTER connection.autoconnect no`
- Disabled OLED service:
  - `sudo systemctl disable --now yahboom_oled.service`

Current status after cleanup:

```text
ROSMASTER hotspot autoconnect: no
yahboom_oled.service: disabled/inactive
rosmaster_main.py: not running
oled_yahboom.pyc: not running
```

The active Wi-Fi profile `TsubashimoNanato` was left unchanged.

## Storage

Robot root filesystem remains tight:

```text
/dev/nvme0n1p1 159G total, 140G used, 12G available, 93% used
```

The deployed adapter workspace is small. No large model or proprietary asset directories were copied into `/home/jetson/workspace/ros2_ws`.

## Buzzer Follow-Up

The buzzer stopped briefly after direct `Rosmaster_Lib.set_beep(0)` commands, then returned after a few seconds. No ROS, Yahboom app, or other user-space process was found holding `/dev/myserial` or reissuing buzzer commands at that time.

Later operator feedback identified this as a hardware false alarm, so the adapter no longer contains periodic buzzer suppression. The ROSMASTER `Buzzer` topic remains available for explicit manual commands.

Clean launch command:

```text
ros2 launch launchers all_nodes.launch
```

When no `DISPLAY` is present, RViz now defaults off so this command no longer produces Qt/XCB display errors over SSH.

## R2 Joystick Initialization

The live robot was reconfigured as an R2-style platform:

- `rosmaster_driver` parameter `car_type`: `5`
- R2 URDF: `yahboomcar_R2.urdf.xacro`
- Front steering is locked at neutral by the adapter.
- Rear motor channels found by direct test:
  - `right_motor_channel=2`
  - `left_motor_channel=4`
- `allow_lateral:=false`; commands are limited to differential-drive `linear.x` and `angular.z`.
- `V max` is `4.0`.

USB controller detected:

```text
Controller on /dev/input/js0
```

Joystick mapping:

- Hold `R2` as the deadman.
- Left-stick vertical drives forward/back.
- Right-stick horizontal commands differential yaw.

ROS nodes verified by the default headless launch:

```text
/aiformula_control/joy_diff_drive_mapper
/aiformula_control/joy_node
/imu_filter_madgwick
/robot_state_publisher
/rosmaster_aiformula_compat_bridge
/rosmaster_base_node
/rosmaster_driver
```

Idle verification:

```text
/aiformula_control/joy_node/joy:
  axes: [-0.0, -0.0, -0.0, -0.0, 1.0, 1.0, 0.0, 0.0]
  buttons: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

/aiformula_control/game_pad/cmd_vel:
  linear.x: 0.0
  angular.z: 0.0

/cmd_vel:
  linear.x: 0.0
  angular.z: 0.0
```

Voltage after the joystick launch:

```text
data: 10.300000190734863
```

## Final Verification

Final build on the robot:

```text
Summary: 3 packages finished [11.7s]
```

Exact no-argument launch verification:

```text
ros2 launch launchers all_nodes.launch
EXACT_LAUNCH_OK
```

Because the SSH session has no `DISPLAY`, RViz auto-disabled and no Qt/XCB error was produced.

Path-test launch verification:

```text
ros2 launch launchers all_nodes.launch use_rviz:=false use_joy:=false
PATH_LAUNCH_OK
```

Driver parameters verified:

```text
drive_mode: rear_motor_diff
xlinear_limit: 4.0
left_motor_channel: 4
right_motor_channel: 2
```

`simple_path_check.sh` result:

```text
voltage: 10.399999618530273
imu: acc=(-0.088, 0.050, -9.818) gyro=(0.007, -0.011, -0.009)
encoders before: [1, 52219, -48, 51866]
encoders after: [1, 54492, -48, 52898]
encoder delta: [0, 2273, 0, 1032]
odom twist: linear.x=-1.000 angular.z=0.000
```

Final zero rear-motor command and neutral front-steering lock were sent after the test.

## Notes

- The adapter-owned `rosmaster_driver_x3` uses `Rosmaster_Lib` directly and avoids launching Yahboom's stock X3/R2 driver executables.
- Yahboom base odometry and description packages are still used:
  - `yahboomcar_base_node`
  - `yahboomcar_description`
- The Sophia-facing launch surface is preserved through the `launchers` package and `/aiformula_*` topics.
