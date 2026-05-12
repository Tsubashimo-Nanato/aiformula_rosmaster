# AI Formula ROSMASTER 适配概览

本仓库用于把 Yahboom ROSMASTER 机器人作为 AI Formula/Sophia 机器人代码的开发和测试平台。

## 当前状态

- 工作空间：`workspace/ros2_ws/src/aiformula`
- 机器人端部署路径：`/home/jetson/workspace/ros2_ws`
- 不修改外部 Sophia 源码；通过 ROSMASTER 工作空间里的兼容层发布 Sophia 风格话题。
- 当前把 ROSMASTER R2 前轮舵机锁在中位，只用后轮电机做差速驱动测试。

## 启动

```bash
cd /home/jetson/workspace/ros2_ws/src/aiformula/launchers/shellscript
./init_sensors.sh
./launch_all_nodes.sh
```

`launch_all_nodes.sh` 会自动 source ROS 2 Humble、Yahboom 工作空间、Yahboom `software/library_ws` 和本工作空间的 `install/setup.bash`。

RViz 默认启动。无显示器或 SSH 运行时使用：

```bash
./launch_all_nodes.sh use_rviz:=false
```

## 手柄控制

- 按住 `R2` 才允许运动。
- 左摇杆上下控制前进和后退。
- 右摇杆左右控制差速转向。
- 默认速度上限：`V max = 4.0`。

## 兼容话题

已发布的主要 Sophia 兼容话题：

- `/aiformula_control/game_pad/cmd_vel`
- `/aiformula_sensing/gyro_odometry_publisher/odom`
- `/aiformula_sensing/wheel_odometry_publisher/odom`
- `/aiformula_sensing/vectornav/imu`
- `/aiformula_sensing/vectornav/velocity_body`
- `/aiformula_sensing/zed_node/imu`
- `/aiformula_sensing/zed_node/left_image/undistorted`
- `/aiformula_sensing/zed_node/right_image/undistorted`
- `/aiformula_sensing/zed_node/depth/depth_registered`
- `/aiformula_sensing/zed_node/point_cloud/cloud_registered`
- `/aiformula_perception/road_detector/mask_image`

说明：ROSMASTER 是单目 RGB 相机加 Orbbec/Astra 深度相机，不是真 ZED。当前右目图像是左目 RGB 图像的副本；点云来自 Orbbec/Astra 深度相机。

## YOLOP

主相机栈启动后，可以单独启动 YOLOP 兼容节点：

```bash
ros2 launch auto_launch auto_yolop_launch.py
```

该节点使用从 `YOLOP_A1` 镜像来的 `yolop-640-640.onnx`，订阅：

- `/aiformula_sensing/zed_node/left_image/undistorted`

发布：

- `/aiformula_perception/road_detector/mask_image`
- `/aiformula_perception/road_detector/mask_image_roi`
- `/aiformula_visualization/road_detector/annotated_mask_image`

## 测试脚本

```bash
cd /home/jetson/workspace/ros2_ws/src/aiformula/launchers/shellscript
./simple_path_check.sh
```
