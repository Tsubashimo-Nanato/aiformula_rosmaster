# AI Formula Sophia Robot Inspection

Date: 2026-05-13  
Requested path: `E:\Mess\Projects\Programming\aiformula_sophia`  
Resolved local path: `E:\Mess\Projects\Programming\aiformula\aiformula_sophia`  
Reference repository named by user: `https://github.com/SophiaControl/AIformula_sophia`  
Local git remote: `https://github.com/Tsubashimo-Nanato/aiformula_sophia.git`

## Scope

This inspection was read-only. Files were read from the AI Formula Sophia fork, and this report was written inside the ROSMASTER workspace only.

The Yahboom/Jetson robot previously inspected is referred to here as the **ROSMASTER robot**.

## High-Level Summary

The AI Formula Sophia repository is a ROS 2 autonomous race-car stack for a mechanically different platform from the ROSMASTER robot.

The Sophia robot is modeled as a larger differential-drive / two-drive-wheel vehicle with a rear caster, CAN motor control, a VectorNav IMU/GNSS stack, and a ZED X stereo camera. Its software is research-oriented and split into perception, sensing, control, navigation, simulation, and trajectory-following packages.

This is not a Yahboom-style all-in-one vendor robot stack. It does not appear to rely on the ROSMASTER proprietary base controller library, OLED display service, LED bar, buzzer, built-in lidar behavior packages, or Orbbec/Astra camera stack.

## Repository Layout

Main source tree:

`E:\Mess\Projects\Programming\aiformula\aiformula_sophia\workspace`

Important top-level packages:

- `common`: shared C++ and Python launch/util helpers
- `control`: motor controller packages
- `launchers`: launch orchestration and topic/frame config
- `sensing`: odometry, rear potentiometer, VectorNav
- `vehicle`: URDF/xacro, ZED X calibration, wheel config
- `perception`: road detector, lane line extraction, lane points, Kalman/filtering, obstacle avoidance
- `navigation`: Nav2 maps and parameters
- `simulator`: Gazebo model/world for `ai_car1`
- `docker`: ROS 2 Foxy AMD Docker files

Additional trajectory workspace:

`E:\Mess\Projects\Programming\aiformula\aiformula_sophia\pid_ws\src\trajectory_follower`

The repository also contains generated `build`, `install`, and `log` output under `pid_ws`.

## Git/Checkout State

The local checkout is not a clean copy of the original tree. Git reports the original `aiformula/...` files as deleted and `workspace/` as untracked. Practically, the source of interest is under `workspace/`, but this layout differs from what git currently tracks.

## Mechanical Structure

The robot model is `ai_car1`.

Physical layout from `workspace/vehicle/xacro/ai_car1.xacro` and simulator SDF:

- Main body: `base_link`
- Root frame: `base_footprint`
- Left drive wheel: `wheel_left_link`
- Right drive wheel: `wheel_right_link`
- Rear caster: `caster_back_link` in xacro, `wheel_caster_link` in simulator
- ZED X camera mounted on the base

Key dimensions/config:

- Wheel radius in xacro: `0.12 m`
- Wheel diameter in config: `0.254 m`
- Wheel tread in config: `0.60 m`
- Gear ratio: `1.1`
- Base mass in xacro/SDF: about `30 kg`
- Drive model: differential drive, not mecanum

This is mechanically very different from the ROSMASTER robot, whose active stack looked like an X3 mecanum platform with four powered mecanum wheels and a Rosmaster controller.

## Sensors

### ZED X Stereo Camera

The Sophia robot uses a Stereolabs ZED X camera through `zed_wrapper`.

Config and calibration:

- Camera name: `zedx` / `zed`
- Serial number used in launch/config: `SN48442725`
- Extrinsic config: `workspace/vehicle/config/zedx/camera_params/SN48442725/extrinsic.yaml`
- Position from extrinsic config:
  - `x: 0.055`
  - `y: 0.0`
  - `z: 0.54`
- Orientation from extrinsic config:
  - roll `-89.0`
  - pitch `0.0`
  - yaw `-90.0`

The launch remaps ZED outputs to:

- `/aiformula_sensing/zed_node/left_image/undistorted`
- `/aiformula_sensing/zed_node/right_image/undistorted`
- `/aiformula_sensing/zed_node/imu`

ZED config includes depth/point-cloud options, but `common.yaml` sets `depth_mode: 'NONE'` by default. Nav2 config nevertheless expects point cloud data at `/aiformula_sensing/zed_node/point_cloud/cloud_registered`, so depth may need to be enabled for full obstacle-costmap navigation.

### VectorNav IMU/GNSS

VectorNav is the main external inertial/GNSS sensor stack.

Config:

- Package: `workspace/sensing/vectornav`
- Port: `/dev/ttyUSB0`
- Default baud: `115200`
- Alternate high-rate config: `921600`
- Frame id: `vectornav`

Launch starts:

- `vectornav`
- `vn_sensor_msgs`

The launcher remaps `vectornav/imu` to:

- `/aiformula_sensing/vectornav/imu`

Topic config also declares:

- `/aiformula_sensing/vectornav/gnss`

The motor controller expects an additional measured body-velocity topic:

- `/aiformula_sensing/vectornav/velocity_body`

That topic is referenced by the controller but was not found as a launcher output in the inspected files, so it may come from VectorNav-specific runtime output, an omitted package, or an external node.

### ZED IMU

The odometry launcher uses the ZED IMU topic, not VectorNav, for the default gyro odometry node:

- input IMU: `/aiformula_sensing/zed_node/imu`
- input CAN: `/aiformula_sensing/vehicle_info`
- output odom: `/aiformula_sensing/gyro_odometry_publisher/odom`

This means the repo contains two IMU sources conceptually: ZED IMU for gyro odometry and VectorNav for dedicated IMU/GNSS sensing.

### Rear Potentiometer

The `rear_potentiometer` package decodes CAN frame `0x11` into rear wheel/caster yaw.

Output:

- `/aiformula_sensing/rear_potentiometer/yaw`

It converts encoded potentiometer bytes into an angle in radians.

## Motors and Low-Level Control

The Sophia robot uses CAN, not a Rosmaster serial API.

CAN setup:

- Shell script loads `kvaser_usb`
- CAN interface: `can0`
- Bitrate: `500000`
- SocketCAN bridge package: `ros2_socketcan`

Startup scripts:

```bash
workspace/launchers/shellscript/can_bringup.sh
workspace/launchers/shellscript/init_sensors.sh
```

Motor command flow:

1. Joystick or trajectory follower publishes `geometry_msgs/Twist`.
2. `motor_controller` subscribes to `/aiformula_control/game_pad/cmd_vel`.
3. Controller converts desired linear/angular velocity into left/right wheel RPM.
4. It publishes an 8-byte CAN frame on `/aiformula_control/motor_controller/reference_signal`.
5. SocketCAN sender sends that frame to `can0`.

Motor CAN details from `motor_controller.py`:

- CAN frame id: `0x210`
- DLC: `8`
- bytes `0-3`: right wheel RPM, signed int32 little-endian
- bytes `4-7`: left wheel RPM, signed int32 little-endian
- publish period: `0.01 s`, roughly `100 Hz`

The current controller is not just a fixed diff-drive mapper. It loads an affine command-correction PyTorch model:

- default model file: `model_controller/affine_command_correction.pt`
- input history features: `cmd_v`, `cmd_omega`, `meas_v`, `meas_omega`
- outputs dynamic affine parameters `a_v`, `a_omega`, `b_v`, `b_omega`
- corrected command is computed as `(base_command - b) / a`

This is a research controller layer. It is fundamentally different from the ROSMASTER robot, where `cmd_vel` is sent directly to the Rosmaster base controller through `Rosmaster_Lib`.

## Odometry

Odometry package:

`workspace/sensing/odometry_publisher`

Available nodes:

- `wheel_odometry_publisher`
- `gyro_odometry_publisher`

Wheel odometry:

- consumes CAN frames
- extracts wheel RPM from CAN frame data
- computes linear velocity and yaw rate from wheel diameter/tread
- publishes `/aiformula_sensing/wheel_odometry_publisher/odom`

Gyro odometry:

- consumes CAN frames plus IMU
- interpolates yaw from IMU
- computes vehicle linear velocity from wheel RPM
- publishes `/aiformula_sensing/gyro_odometry_publisher/odom`

The main launch uses `gyro_odometry_publisher`.

## Perception

### Road Detector

Package:

`workspace/perception/road_detector`

Purpose:

- YOLOP/YOLOPv2-style road/lane segmentation
- TensorRT runtime through `tensorrt` and `pycuda`
- subscribed image: ZED X left undistorted image
- publishes road/lane mask images

Important files:

- `road_detector/road_detector.py`
- `weights/yolopv2_fp16.engine`
- `weights/End-to-end.pth`

Launch remaps:

- input: `/aiformula_sensing/zed_node/left_image/undistorted`
- mask output: `/aiformula_perception/road_detector/mask_image`
- annotated output: `/aiformula_visualization/road_detector/annotated_mask_image`

### Lane Line Publisher

Package:

`workspace/perception/lane_line_publisher`

Purpose:

- consumes binary lane mask image
- finds lane pixels
- transforms lane pixels from camera frame into vehicle frame
- fits cubic lane lines
- publishes left/right/center lane lines as `PointCloud2`

Outputs:

- `/aiformula_perception/lane_line_publisher/lane_lines/left`
- `/aiformula_perception/lane_line_publisher/lane_lines/right`
- `/aiformula_perception/lane_line_publisher/lane_lines/center`

Config:

- ROI in vehicle frame: `x = 1.5..10.0 m`, `y = -3.0..3.0 m`
- point spacing: `0.5 m`

### Lane Points, Filtering, and Obstacle Avoidance

Packages:

- `lane_points`
- `kalman_filter`
- `obsticle_avoidence` spelling as in repo

Typical pipeline from README:

```bash
ros2 launch road_detector road_detector.launch.py
ros2 launch lane_line_publisher lane_line_publisher.launch.py
ros2 run lane_points lane_0529oa
ros2 run kalman_filter withoutkalman_0312
ros2 run obsticle_avoidence b_spline
ros2 run trajectory_follower lya_oa
```

Lane point flow:

- lane lines are reduced into three `Pose2D` points:
  - `/processed_point_a`
  - `/processed_point_b`
  - `/processed_point_c`
- filter publishes:
  - `filtered_lane_pose`
  - `filtered_omega_t`
- trajectory follower consumes those and publishes velocity commands.

Obstacle avoidance code detects red/cone-like obstacles from camera images or masks, pauses lane forwarding with `/lane_stop_flag`, generates B-spline/NURBS avoidance points, and publishes replacement path points.

## Trajectory Following

Trajectory follower source:

`pid_ws/src/trajectory_follower`

Important executables:

- `lya_follower_connected_omegat_global`
- `lya_oa`
- `lya_record`
- `lya_follower_fixedpath_record`
- `lya_baseline_follower_fixedpath_record`

The live lane-following follower:

- subscribes to `/aiformula_sensing/gyro_odometry_publisher/odom`
- subscribes to `/filtered_lane_pose`
- subscribes to `/filtered_omega_t`
- transforms local lane targets into `odom`
- publishes `/aiformula_control/game_pad/cmd_vel`

The controller is an LYA-style trajectory controller with velocity and angular velocity limits, not the ROSMASTER teleop/bringup controller.

## Main Launch Flow

Core launch:

```bash
ros2 launch launchers all_nodes.launch.py
```

It starts:

- vehicle TF/static robot description
- ZED X camera wrapper
- VectorNav
- joystick node
- `teleop_twist_joy`
- motor controller
- SocketCAN receiver/sender
- gyro odometry publisher
- rear potentiometer decoder

The fork also has `our_all_nodes.launch.py`, which includes lane line publishing and has a broken-looking reference to `our_zedx_camera.launch.py`; the actual file present is `ournew_zedx_camera.launch.py`.

## Navigation and Simulation

Navigation:

- Nav2 config in `workspace/navigation`
- map files from RTAB-Map and sample maps
- AMCL and DWB local planner configured for differential drive
- costmaps are configured to consume ZED point cloud data

Simulation:

- Gazebo model `ai_car1`
- differential drive plugin
- simulated camera
- simulated IMU
- wheel joints for left/right and caster

## Comparison With ROSMASTER Robot

Major differences:

- ROSMASTER robot: Yahboom/ROSMASTER Jetson robot with proprietary Rosmaster controller library, OLED service, Orbbec camera, optional lidar packages, buzzer/RGB/LED control, and X3 mecanum-style software.
- Sophia robot: AI Formula research vehicle with two powered wheels, rear caster, CAN motor control, ZED X camera, VectorNav IMU/GNSS, lane segmentation, lane geometry extraction, trajectory following, Nav2, and Gazebo simulation.
- ROSMASTER motor path: `cmd_vel -> Rosmaster_Lib -> /dev/myserial -> base controller`.
- Sophia motor path: `cmd_vel -> motor_controller -> CAN frame 0x210 -> ros2_socketcan -> can0`.
- ROSMASTER odometry source: Rosmaster controller raw velocity plus IMU/mag from controller.
- Sophia odometry source: wheel RPM over CAN plus ZED/VectorNav inertial data.
- ROSMASTER perception stack: vendor robot demos, Orbbec/Astra, lidar behaviors, visual tracking demos.
- Sophia perception stack: ZED X lane segmentation, cubic lane-line fitting, PointCloud2 lane geometry, Kalman-like filtering, B-spline obstacle avoidance.
- ROSMASTER appears packaged as a multi-feature educational robot platform.
- Sophia appears built for autonomous race-course/lane-following research.

## Risks and Notes

- The local git state is unusual: `workspace/` is untracked while the older tracked `aiformula/` tree is deleted.
- Several files contain mojibake/encoding-damaged Chinese comments, though code structure is still readable.
- Some README commands refer to paths such as `workspace/ros2_ws/src/aiformula`, while this local fork is laid out as `workspace/`.
- `road_detector.launch.py` declares `onnx_path`, but the current `road_detector.py` expects `engine_path`; the package also contains a TensorRT engine file. This mismatch may matter at runtime.
- `our_all_nodes.launch.py` references `our_zedx_camera.launch.py`, but the inspected tree contains `ournew_zedx_camera.launch.py`.
- The motor controller expects `/aiformula_sensing/vectornav/velocity_body`, but the inspected launch/config files did not clearly show which node publishes it.
