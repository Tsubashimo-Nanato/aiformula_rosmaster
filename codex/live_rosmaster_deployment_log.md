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
./launch_all_nodes.sh
```

`launch_all_nodes.sh` sources all required setup files before calling the extensionless-style `all_nodes.launch` wrapper.

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
cd /home/jetson/workspace/ros2_ws/src/aiformula/launchers/shellscript
./launch_all_nodes.sh
```

The wrapper sources ROS 2 Humble, the Yahboom workspace, and the ROSMASTER adapter workspace before launching. RViz is on by default; use `./launch_all_nodes.sh use_rviz:=false` for headless SSH runs.

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

Previous exact no-argument launch verification:

```text
ros2 launch launchers all_nodes.launch
EXACT_LAUNCH_OK
```

At that time RViz auto-disabled over SSH. The current requested behavior is RViz on by default; use `use_rviz:=false` for headless SSH runs.

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

## 2026-05-13 Update: Differential Steering And Camera Topics

Latest deployed build:

```text
Summary: 3 packages finished
```

Current launch PID:

```text
8378
```

Changes:

- Joystick yaw axis changed to `2`, matching right-stick horizontal on the detected DragonRise controller.
- Rear-motor diff drive now uses normalized mixing:
  - full forward: both rear motors forward
  - full yaw: rear motors counter-rotate
  - combined forward/yaw: mixed and normalized to avoid overdriving
- The wrapper now sources Yahboom `software/library_ws`, which exposes `astra_camera` and lidar/camera support packages.
- ROSMASTER USB RGB camera and Orbbec depth camera now start by default.

New/verified aiformula-compatible topics:

```text
/odom
/aiformula_sensing/wheel_odometry_publisher/odom
/aiformula_sensing/zed_node/imu
/aiformula_sensing/zed_node/left_image/undistorted
/aiformula_sensing/zed_node/right_image/undistorted
/aiformula_sensing/zed_node/left/camera_info
/aiformula_sensing/zed_node/right/camera_info
/aiformula_sensing/zed_node/depth/depth_registered
/aiformula_sensing/zed_node/depth/camera_info
/aiformula_sensing/zed_node/point_cloud/cloud_registered
```

Notes:

- Right ZED image is currently a copy of the monocular USB RGB camera.
- Point cloud comes from the Orbbec/Astra depth camera at `/camera/depth/points`.
- A direct `/cmd_vel` yaw test with `angular.z=4.0` changed rear encoder channels in opposite directions:

```text
before: [1, 246829, -176, 203524]
after:  [1, 256433, -176, 194108]
```

## 2026-05-13 Update: YOLOP_A1 Compatibility

Added ROS packages:

```text
road_detector
auto_launch
```

Mirrored from:

```text
E:\Mess\Projects\Programming\aiformula\YOLOP\YOLOP_A1
```

Runtime artifact:

```text
road_detector/weights/yolop-640-640.onnx
```

Build result on robot:

```text
Summary: 2 packages finished [9.39s]
MODEL_INPUTS [('images', [1, 3, 640, 640], 'tensor(float)')]
MODEL_OUTPUTS [('det_out', [1, 25200, 6], 'tensor(float)'), ('drive_area_seg', [1, 2, 640, 640], 'tensor(float)'), ('lane_line_seg', [1, 2, 640, 640], 'tensor(float)')]
```

Launch command:

```bash
ros2 launch auto_launch auto_yolop_launch.py
```

Current YOLOP launch PID:

```text
12277
```

Verified node:

```text
/aiformula_perception/road_detector
```

Verified topics:

```text
/aiformula_sensing/zed_node/left_image/undistorted [sensor_msgs/msg/Image]
/aiformula_perception/road_detector/mask_image [sensor_msgs/msg/Image]
/aiformula_perception/road_detector/mask_image_roi [sensor_msgs/msg/Image]
/aiformula_visualization/road_detector/annotated_mask_image [sensor_msgs/msg/Image]
```

Mask sample:

```text
height: 480
width: 640
encoding: mono8
step: 640
```

Observed mask publish rate:

```text
~8.7 Hz
```

Runtime provider:

```text
CUDAExecutionProvider, CPUExecutionProvider
```

## 2026-05-13 Update: YOLOP Epoch 240

Requested checkpoint:

```text
E:\Mess\Projects\Programming\aiformula\YOLOP\YOLOP_A1\runs\LaneDataset\lane_only\_2026-04-24-16-47\epoch-240.pth
```

Exported on the Jetson with `road_detector/tools/export_lane_checkpoint.py` to:

```text
road_detector/weights/yolop-epoch-240-640.onnx
```

ONNX verification:

```text
inputs:  images [1, 3, 640, 640]
outputs: lane_line_seg [1, 2, 640, 640]
providers: CUDAExecutionProvider, CPUExecutionProvider
```

Robot rebuild and restart:

```text
Summary: 2 packages finished [9.39s]
main launch PID: 14145
YOLOP launch PID: 14368
```

Runtime verification after restart:

```text
/aiformula_perception/road_detector active
/rviz2 active
mask_image: 640x480 mono8
mask_image rate: ~13.5 Hz
voltage: 11.5 V
```
