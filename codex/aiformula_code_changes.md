# AI Formula Code Changes

No files in the external Sophia/AI Formula source tree were modified.

This repository uses compatibility packages under `workspace/ros2_ws/src/aiformula` to expose Sophia-style topics on the ROSMASTER robot:

- `/aiformula_control/game_pad/cmd_vel`
- `/aiformula_sensing/gyro_odometry_publisher/odom`
- `/aiformula_sensing/vectornav/imu`
- `/aiformula_sensing/vectornav/velocity_body`

The current ROSMASTER driver locks the R2 front steering servos at neutral and drives the two rear motor channels as a differential-drive test platform.
