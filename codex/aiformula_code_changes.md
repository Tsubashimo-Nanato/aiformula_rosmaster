# AI Formula Code Changes

No files in the external Sophia/AI Formula source tree were modified.

This repository uses compatibility packages under `workspace/ros2_ws/src/aiformula` to expose Sophia-style topics on the ROSMASTER robot:

- `/aiformula_control/game_pad/cmd_vel`
- `/aiformula_sensing/gyro_odometry_publisher/odom`
- `/aiformula_sensing/wheel_odometry_publisher/odom`
- `/aiformula_sensing/vectornav/imu`
- `/aiformula_sensing/vectornav/velocity_body`
- `/aiformula_sensing/zed_node/imu`
- `/aiformula_sensing/zed_node/left_image/undistorted`
- `/aiformula_sensing/zed_node/right_image/undistorted`
- `/aiformula_sensing/zed_node/point_cloud/cloud_registered`

The current ROSMASTER driver locks the R2 front steering servos at neutral and drives the two rear motor channels as a differential-drive test platform.

Latest ROSMASTER-specific changes:

- Joystick yaw is mapped to right-stick horizontal axis `2`.
- Rear motor differential drive uses normalized command mixing, so yaw commands counter-rotate the rear motors instead of using a weak physical-tread conversion.
- ROSMASTER USB RGB camera is bridged to the ZED image topic names.
- ROSMASTER Orbbec/Astra depth camera is bridged to the ZED point-cloud/depth topic names.
