# ROSMASTER to AI Formula Adaptation Roadmap

Date: 2026-05-13

Workspace root: `E:\Mess\Projects\Programming\aiformula\ROSMASTER`

This roadmap started from local mirrors and was later updated with live ROSMASTER deployment findings.

## Local Mirrors

- Sophia source snapshot: `mirrors/aiformula_sophia`
  - Copied from `E:\Mess\Projects\Programming\aiformula\aiformula_sophia`.
  - Includes `workspace/` and `pid_ws/src/trajectory_follower`.
- ROSMASTER robot snapshot: `mirrors/rosmaster_robot`
  - Copied read-only over SSH from `jetson@192.168.0.38`.
  - Includes Yahboom base/bringup/control/description/nav/lidar packages, selected app startup files, NetworkManager/systemd/udev config, Rosmaster Python eggs, and extracted `Rosmaster_Lib` source.
  - Bulk ROSMASTER vision/model assets were intentionally not copied unless they were needed for bringup analysis.

## Key Structural Difference

The migration should not try to make ROSMASTER mechanically identical to Sophia.

- ROSMASTER: live robot is R2-style with front steering and two rear drive motors, `Rosmaster_Lib`, serial controller on `/dev/myserial`, low-level command API `set_car_motion(vx, vy, wz)`, onboard IMU/magnetometer/voltage/LED/buzzer support, USB camera support, optional lidar packages, Yahboom app/hotspot startup.
- Sophia: AI Formula differential-drive platform, SocketCAN/Kvaser `can0` at 500 kbit/s, motor command frame `0x210`, VectorNav IMU/GNSS, ZED X camera, rear potentiometer CAN frame `0x11`, Sophia topic namespaces under `/aiformula_*`.

The right first goal is a compatibility platform:

1. Keep ROSMASTER low-level motor/IMU access.
2. Expose Sophia-style topics and frames.
3. Run Sophia planning/control/perception pieces against ROSMASTER-compatible sensor streams where feasible.
4. Replace or bypass Sophia hardware-specific nodes when the underlying hardware is absent.

## ROSMASTER Components To Keep

- `Rosmaster_Lib` as the hardware abstraction for the motor controller, IMU, voltage, RGB LED bar, and buzzer.
- `/dev/myserial` udev rule from `etc/udev/rules.d/serial.rules`.
- `yahboomcar_bringup/yahboomcar_bringup/Ackman_driver_R2.py` as the R2 reference for car type, raw velocity, IMU, magnetometer, voltage, and LED/buzzer topics.
- `yahboomcar_bringup/yahboomcar_bringup/Mcnamu_driver_X3.py` and `yahboomcar_base_node/src/base_node_X3.cpp` remain useful references for direct angular-velocity odometry integration while front steering is ignored.
- `yahboomcar_description/urdf/yahboomcar_R2.urdf.xacro` as the physical geometry reference.
- Orbbec/Astra camera rules and the mirrored `ros2_astra_camera` source for camera bringup experiments.

## ROSMASTER Components To Remove Or Disable Later

Do this only in a deployment step after local scripts are prepared and reviewed.

- GNOME autostart file: `/home/jetson/.config/autostart/bash.desktop`
  - Starts `/home/jetson/Rosmaster/rosmaster/start_app.sh`.
- App startup script: `/home/jetson/Rosmaster/rosmaster/start_app.sh`
  - Runs `rosmaster_main.py` in `gnome-terminal`.
- Yahboom app server: `/home/jetson/Rosmaster/rosmaster/rosmaster_main.py`
  - Opens TCP control on port 6000 and a gevent/Flask service on port 6500.
- Hotspot NetworkManager profile: `/etc/NetworkManager/system-connections/Hotspot.nmconnection`
  - Configured as Wi-Fi AP mode with SSID `ROSMASTER`.
- OLED service: `/etc/systemd/system/yahboom_oled.service`
  - Starts `/home/jetson/software/oled_yahboom/yahboom_oled.pyc`.
- Yahboom joystick nodes in stock launch files unless joystick testing is explicitly needed.

## Topic Compatibility Target

First compatibility layer should map Sophia topics to ROSMASTER functionality.

| Sophia expectation | ROSMASTER source or replacement | First implementation |
| --- | --- | --- |
| `/aiformula_control/game_pad/cmd_vel` (`geometry_msgs/Twist`) | ROSMASTER driver consumes `cmd_vel` | Remap or adapter node forwards to ROSMASTER motor driver |
| `/aiformula_sensing/gyro_odometry_publisher/odom` (`nav_msgs/Odometry`) | ROSMASTER `odom_raw` / EKF odom | Republish or remap ROSMASTER odom into Sophia topic |
| `/aiformula_sensing/vectornav/velocity_body` (`nav_msgs/Odometry`) | ROSMASTER velocity from `vel_raw` or odom twist | Publish body velocity compatibility odom |
| `/aiformula_sensing/vectornav/imu` (`sensor_msgs/Imu`) | ROSMASTER `imu/data_raw` or filtered IMU | Republish to Sophia IMU topic |
| `/aiformula_sensing/zed_node/left_image/undistorted` | Orbbec/Astra or USB camera image | Camera bridge with calibration clearly marked non-ZED |
| `/aiformula_control/motor_controller/reference_signal` (`can_msgs/Frame`) | Sophia CAN motor command | Optional shim only if testing Sophia motor_controller itself |
| `/aiformula_sensing/rear_potentiometer/yaw` | No ROSMASTER equivalent | Publish fixed zero or omit until a steering/yaw sensor exists |

## Recommended Architecture

Create an overlay ROS 2 workspace under `rosmaster_aiformula_ws/src` with small packages instead of editing mirrored vendor snapshots.

Proposed packages:

- `rosmaster_aiformula_bringup`
  - Launches ROSMASTER hardware driver without Yahboom app/hotspot/joystick behavior.
  - Includes Sophia compatibility topic remaps.
- `rosmaster_aiformula_bridge`
  - Republish/remap nodes for odometry, IMU, body velocity, camera images, and optional CAN-frame shim.
- `rosmaster_aiformula_description`
  - ROSMASTER physical geometry with Sophia frame names where practical: `map`, `odom`, `base_footprint`, `base_link`, camera frames.
- `rosmaster_aiformula_config`
  - Robot-specific calibration, limits, and launch parameters.
- `rosmaster_deploy_tools`
  - Scripts for disabling Yahboom autostart/hotspot/OLED on the live robot after review.

## Motor Strategy

Start with Sophia's differential-drive command surface, but bypass Sophia's CAN output for actual ROSMASTER driving.

Reason:

- Sophia `motor_controller` is trained/tuned for a differential-drive AI Formula chassis and publishes CAN frame `0x210`.
- ROSMASTER already has a working low-level serial controller with `set_car_motion(vx, vy, wz)`.
- The live Jetson has `joy`, `teleop_twist_joy`, and `torch`, but not `can_msgs`; Sophia's current `motor_controller` cannot run as-is until that message dependency and a CAN-to-ROSMASTER shim are added.
- The current safe first step keeps the Sophia `/aiformula_control/game_pad/cmd_vel` interface and differential-drive semantics, then maps to ROSMASTER serial commands with the front steering left untouched.

First driving path:

```text
/aiformula_control/game_pad/cmd_vel
  -> ROSMASTER compatibility bridge
  -> rosmaster_driver cmd_vel
  -> Rosmaster_Lib.set_car_motion(vx, 0, wz), car_type=5
  -> serial controller on /dev/myserial
```

Current joystick path:

```text
/aiformula_control/joy_node/joy
  -> joy_diff_drive_mapper
  -> /aiformula_control/game_pad/cmd_vel
```

The mapper requires `R2` as a deadman, uses left-stick vertical for `linear.x`, and uses right-stick horizontal for `angular.z`.

Optional test-only path:

```text
Sophia motor_controller
  -> /aiformula_control/motor_controller/reference_signal (CAN frame 0x210)
  -> CAN-to-Rosmaster shim
  -> convert left/right RPM to approximate vx/wz
  -> Rosmaster_Lib.set_car_motion(vx, 0, wz)
```

The optional path is useful for testing Sophia's model-correction node, but not as the default robot bringup.

Keep `suppress_buzzer:=true` in ROSMASTER bringup until the battery and controller alarm behavior are characterized. On the live robot, the buzzer repeatedly returned after direct buzzer-off commands while voltage was about `9.7 V`, which is consistent with a controller low-voltage alarm rather than a competing ROS process.

## Perception Strategy

Treat camera compatibility as a separate phase.

- Sophia perception expects ZED X topics and calibration.
- ROSMASTER currently presents Orbbec/Astra/USB-style camera support, not ZED X.
- First target is a topic-level image bridge so perception nodes can start.
- Lane geometry and calibration must then be retuned for ROSMASTER camera height, pitch, lens, field of view, and coordinate frames.
- Do not assume Sophia's lane detector results are geometrically valid on ROSMASTER until camera calibration and transforms are verified.

## Deployment Cleanup Strategy

Prepare local scripts before touching the live robot.

Local dry-run helpers now exist:

- `scripts/rosmaster_disable_vendor_startup.sh`
- `scripts/rosmaster_restore_vendor_startup.sh`

The live robot has also been configured with the minimal cleanup captured in `codex/live_rosmaster_deployment_log.md`.

1. Stop app process if running: `rosmaster_main.py`.
2. Disable GNOME autostart for `bash.desktop`.
3. Disable or remove the NetworkManager `Hotspot` autoconnection.
4. Disable `yahboom_oled.service` if the display is no longer needed.
5. Keep `nvwifibt.service`, base Wi-Fi drivers, udev rules, and serial/lidar/camera rules unless there is a specific reason to remove them.
6. Add a reviewed replacement service or launch command for the ROSMASTER AI Formula bringup.

## Implementation Phases

### Phase 1: Local Overlay Skeleton

- Create ROS 2 package skeletons under `rosmaster_aiformula_ws/src`.
- Add a bringup launch that starts only the ROSMASTER driver, odom, IMU filter, robot state publisher, and compatibility bridge.
- Exclude Yahboom app, hotspot startup, OLED, RViz, and Yahboom joystick by default.

### Phase 2: Topic Bridge

- Implement ROSMASTER-to-Sophia odom bridge.
- Implement ROSMASTER-to-Sophia IMU bridge.
- Implement Sophia cmd_vel-to-ROSMASTER command bridge.
- Add conservative velocity limits matching the current R2-style differential-drive test mode:
  - joystick `vx`: `[-0.25, 0.25]`
  - joystick `wz`: `[-0.6, 0.6]`
  - bridge `vx`: `[-0.35, 0.35]`
  - bridge `wz`: `[-0.8, 0.8]`
- Force `vy` to `0.0` for AI Formula differential-drive compatibility.

### Phase 3: Description And Frames

- Build a ROSMASTER description package using the R2 URDF as reference.
- Preserve Sophia frame IDs where possible:
  - `odom`
  - `base_footprint`
  - `base_link`
  - camera optical frame aliases
- Add static transforms needed by Sophia perception/control nodes.

### Phase 4: Camera Bringup

- Bring up ROSMASTER camera through Orbbec/Astra or USB camera path.
- Publish image topics compatible with Sophia's expected ZED left image topic.
- Add calibration files under local config.
- Verify image orientation, exposure, frame rate, and timestamp behavior.

### Phase 5: Sophia Stack Subset

- Start with teleop and trajectory follower pieces that publish `/aiformula_control/game_pad/cmd_vel`.
- Run odometry consumers against the compatibility odom.
- Add perception only after camera bridge and calibration are stable.
- Keep Sophia CAN, VectorNav, ZED X, and rear potentiometer launch includes disabled unless emulated or replaced.

### Phase 6: Live Robot Deployment

- Copy/install only the overlay workspace and reviewed cleanup scripts to ROSMASTER.
- Build on the Jetson against ROS 2 Humble.
- Test with wheels lifted before floor tests.
- Add a systemd user or system service only after manual launch is stable.

## Safety Checklist For First Motion

- Confirm no Yahboom app process is running.
- Confirm only one node is commanding the base.
- Confirm `/dev/myserial` exists and points to the CH340 serial controller.
- Start with velocity limits much lower than the hardware maximum.
- Test `/aiformula_control/game_pad/cmd_vel` with wheels lifted.
- Verify positive `linear.x` drives forward in the expected Sophia frame convention.
- Verify positive `angular.z` rotates counterclockwise in ROS convention.
- Verify odom twist signs match command signs.
- Verify emergency stop path: publish zero Twist and stop the driver process if needed.

## Open Questions

- Whether ROSMASTER should eventually emulate Sophia CAN topics for regression tests, or whether CAN-specific logic should remain Sophia-only.
- Whether the ROSMASTER camera should be Orbbec/Astra depth, USB RGB only, or a future ZED-compatible camera.
- Whether the LED bar, buzzer, OLED, and lidar should be exposed through compatibility diagnostics or removed entirely.
- Whether the final deployment should use systemd, a tmux/manual launch workflow, or Docker.
