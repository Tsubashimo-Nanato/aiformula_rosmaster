# Jetson Mobile Robot Inspection

Date: 2026-05-13  
Verified target: `192.168.0.38`  
Hostname: `yahboom`  
SSH user: `jetson`  
Earlier attempted target: `192.168.1.42`, unreachable from this workstation

## Summary

The device at `192.168.0.38` is a Yahboom/ROSMASTER-style mobile robot running ROS 2 Humble on a Jetson Orin Nano. The installed robot stack is under:

`/home/jetson/yahboomcar_ros2_ws/yahboomcar_ws`

The software includes Yahboom X1, X3, and R2 variants. Initial inspection over-weighted the X3 software because those packages were prominent in the installed tree. Later live configuration confirmed this robot should be treated as an R2-style platform with front steering and two rear drive motors. The current adapter uses `car_type=5`, the R2 URDF, and ignores front steering while testing differential-drive behavior.

At inspection time, the full ROS robot bringup was not running. `ros2 node list` showed no active robot nodes, and the only ROS topics visible were `/parameter_events` and `/rosout`. The active robot-related service was the Yahboom OLED service.

## Compute Platform

- Jetson model: `NVIDIA Jetson Orin Nano Engineering Reference Developer Kit Super`
- OS: Ubuntu `22.04.5 LTS`
- Kernel: `5.15.148-tegra`
- L4T: `R36.4.3`, dated `2025-01-08`
- ROS: ROS 2 Humble installed at `/opt/ros/humble`
- Network: Wi-Fi interface `wlP1p1s0` at `192.168.0.38/24`
- Docker and JupyterLab are enabled services.

## Physical Devices Observed

Confirmed by `lsusb`, `/dev`, and udev rules:

- Base controller link: CH340 USB serial converter, `1a86:7523`
  - Kernel device: `/dev/ttyUSB0`
  - Udev symlink: `/dev/myserial -> ttyUSB0`
  - Used by `Rosmaster_Lib` default constructor as `/dev/myserial` at `115200` baud.
- Depth/RGB camera: Orbbec USB devices
  - `2bc5:060f` Orbbec depth sensor
  - `2bc5:050f` Orbbec USB 2.0 camera
  - V4L2 devices: `/dev/video0`, `/dev/video1`
- USB camera device name from V4L2: `USB 2.0 Camera: USB Camera`
- CAN interface exists as `can0`, but it was down during inspection.
- Multiple I2C buses exist: `/dev/i2c-0`, `1`, `2`, `4`, `5`, `7`, `9`, `10`, `11`.
- No `/dev/rplidar` or `/dev/ydlidar` symlink was present during inspection.

## Sensors

### IMU and Magnetometer

The IMU is exposed through the Rosmaster base controller, not as a separate USB IMU device.

The X3 driver creates `Rosmaster()` from `Rosmaster_Lib`, reads:

- `get_accelerometer_data()`
- `get_gyroscope_data()`
- `get_magnetometer_data()`

It publishes:

- `imu/data_raw` as `sensor_msgs/Imu`
- `imu/mag` as `sensor_msgs/MagneticField`

The launch file starts `imu_filter_madgwick_node`, configured by `yahboomcar_bringup/param/imu_filter_param.yaml`:

- fixed frame: `base_link`
- magnetometer use: `false`
- TF publishing: `false`
- world frame: `enu`

`robot_localization` is also launched for X3 via `ekf_x1_x3_launch.py`, using a two-dimensional EKF configuration.

### Camera

An Orbbec depth/RGB camera is physically present. The software includes `astra_camera` and OpenNI ROS 2 support.

The Astra launch config supports:

- color stream, default `640x480 @ 30 FPS`
- depth stream, default `640x480 @ 30 FPS`
- IR stream
- point cloud publishing
- TF publishing

The Yahboom workspace also includes camera-based packages:

- `yahboomcar_astra`
- `yahboomcar_visual`
- `yahboomcar_KCFTracker`
- `yahboomcar_linefollow`
- YOLO/Ultralytics software under `/home/jetson/software` and `/home/jetson/ultralytics`
- non-ROS road-following examples under `/home/jetson/Rosmaster/auto_drive`

### Lidar

The robot description includes a `laser_link`, and the workspace contains lidar drivers and launch files:

- `sllidar_ros2`
- `ydlidar_ros2_driver`
- `yahboomcar_laser`

Yahboom laser behavior launch files include:

- `laser_Avoidance_a1_X3.launch.py`
- `laser_Tracker_a1_X3.launch.py`
- `laser_Warning_a1_X3.launch.py`

However, no physical lidar serial device was confirmed during this inspection. The usual udev links `/dev/rplidar` and `/dev/ydlidar` were absent, and `lsusb` did not show a separate CP210x/PL2303-style lidar serial adapter. The software supports lidar, but the hardware was either not connected, not powered, or not identifiable as a separate device at inspection time.

## Motors and Drive

The X3 robot model is mecanum/four-wheel omnidirectional in the URDF:

- `front_right_wheel`
- `front_left_wheel`
- `back_right_wheel`
- `back_left_wheel`
- continuous wheel joints for all four wheels
- `base_link`, `base_footprint`, `imu_link`, `laser_link`, and `camera_link`

Motor commands flow through ROS topic `cmd_vel`.

For X3:

1. `yahboom_joy_X3` or navigation publishes `geometry_msgs/Twist` on `cmd_vel`.
2. `Mcnamu_driver_X3` subscribes to `cmd_vel`.
3. `Mcnamu_driver_X3` sends `vx`, `vy`, and `angular.z` to the Rosmaster controller with `self.car.set_car_motion(vx, vy, angular)`.
4. `Rosmaster_Lib` communicates with the controller over `/dev/myserial` at `115200` baud.
5. The controller reports motion, battery, IMU, and magnetometer data back to the Jetson.

The X3 driver publishes:

- `vel_raw` as `geometry_msgs/Twist`
- `joint_states` as `sensor_msgs/JointState`
- `voltage` as `std_msgs/Float32`
- `edition` as `std_msgs/Float32`
- `imu/data_raw`
- `imu/mag`

`base_node_X3` subscribes to `vel_raw` and integrates it into `odom_raw` as `nav_msgs/Odometry`. It can optionally publish odom TF, but the X3 launch defaults `pub_odom_tf` to `false` because EKF is expected to publish the fused transform.

## ROS 2 Workspace Structure

Primary workspace:

`/home/jetson/yahboomcar_ros2_ws/yahboomcar_ws`

Important packages:

- `yahboomcar_bringup`: launch files and low-level Rosmaster drivers
- `yahboomcar_base_node`: converts raw velocity to odometry
- `yahboomcar_ctrl`: joystick and keyboard control
- `yahboomcar_description`: X3/R2 robot models, meshes, RViz configs
- `yahboomcar_description_x1`: X1 model
- `yahboomcar_laser`: lidar avoidance/tracking/warning behaviors
- `yahboomcar_nav`: Nav2 navigation launch/config/maps
- `yahboomcar_slam`: Cartographer, gmapping, ORB-SLAM, point cloud, and octomap launches
- `yahboomcar_astra`: Astra/Orbbec camera color tracking
- `yahboomcar_visual`: QR/object/vision examples
- `yahboomcar_mediapipe`: MediaPipe examples
- `yahboomcar_msgs`: custom messages for images, targets, positions, and point arrays
- `yahboomcar_multi`: multi-robot launch and navigation files

Library workspace:

`/home/jetson/yahboomcar_ros2_ws/software/library_ws`

Notable installed libraries:

- `robot_localization`
- `sllidar_ros2`
- `ydlidar_ros2_driver`
- `astra_camera`
- `cartographer_ros`
- `slam_gmapping`
- `teb_local_planner`
- `web_video_server`

## Main Bringup Flow

The likely X3 bringup command is:

```bash
source /opt/ros/humble/setup.bash
source /home/jetson/yahboomcar_ros2_ws/yahboomcar_ws/install/setup.bash
ros2 launch yahboomcar_bringup yahboomcar_bringup_X3_launch.py
```

That launch starts:

- `robot_state_publisher`
- `joint_state_publisher`
- `Mcnamu_driver_X3`
- `base_node_X3`
- `imu_filter_madgwick_node`
- `robot_localization` EKF launch
- `yahboom_joy_X3`
- `joy_node`

RViz is defined but commented out in the launch description.

## Navigation, SLAM, and Behaviors

The installed stack supports:

- Manual joystick teleop via `yahboom_joy_X3` and `joy_node`
- Keyboard teleop via `yahboom_keyboard`
- Nav2 navigation through `yahboomcar_nav`
- SLAM through `yahboomcar_slam`
- Cartographer/gmapping support through the library workspace
- ORB-SLAM RGB-D/mono/stereo launch files
- Point cloud mapping and octomap launch files
- Lidar avoidance, tracking, and warning behaviors
- Camera color tracking and KCF tracking
- Line following

## Non-ROS Rosmaster Software

There is also a non-ROS Yahboom/Rosmaster application tree:

`/home/jetson/Rosmaster`

It contains:

- TCP/Web control code in `rosmaster/rosmaster_main.py`
- camera handling in `rosmaster/camera_rosmaster.py`
- Jupyter/AI road following examples in `auto_drive`
- STM32 board firmware project folders for motor, encoder, IMU, CAN, serial, LED, buzzer, RGB strip, and servo features

This appears to be a vendor demo/control stack separate from the ROS 2 workspace.

## Runtime State During Inspection

Running robot-related service:

- `yahboom_oled.service`
  - command: `python3 /home/jetson/software/oled_yahboom/yahboom_oled.pyc`
  - enabled and running

Running infrastructure:

- `docker.service`
- `containerd.service`
- `jupyterlab.service`

Not running at inspection time:

- No active Yahboom ROS 2 bringup nodes
- No active lidar node
- No active camera ROS node
- No active navigation or SLAM nodes

## Notes and Uncertainties

- The software strongly indicates an X3 mecanum configuration, but because the robot bringup was not active, the live ROS graph did not confirm the active robot variant.
- The Orbbec camera is physically confirmed.
- The base controller, motor controller path, battery/IMU source, and serial link are physically confirmed through `/dev/myserial -> ttyUSB0` and the Rosmaster driver code.
- Lidar support is installed and modeled in URDF, but no physical lidar device was visible at inspection time.
- The first IP supplied, `192.168.1.42`, was not reachable from the workstation. The successful target was `192.168.0.38`.
