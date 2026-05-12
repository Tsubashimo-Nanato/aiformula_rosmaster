# AI Formula ROSMASTER 适配概览

本仓库用于把 ROSMASTER 机器人作为 AI Formula/Sophia 的开发和测试平台。

## 当前状态

- 工作空间：`workspace/ros2_ws/src/aiformula`
- 机器人端部署路径：`/home/jetson/workspace/ros2_ws`
- 不修改外部 Sophia 源码；通过兼容层发布和订阅 Sophia 风格的话题。
- 当前把 ROSMASTER R2 前轮舵机锁在中位，只用两个后轮电机做差速测试。

## 启动

```bash
cd /home/jetson/workspace/ros2_ws/src/aiformula/launchers/shellscript
./init_sensors.sh
./launch_all_nodes.sh
```

`launch_all_nodes.sh` 会自动 source ROS 2、Yahboom 工作空间和本工作空间的 `install/setup.bash`。

RViz 默认启动。无显示器或 SSH 运行时使用：

```bash
./launch_all_nodes.sh use_rviz:=false
```

## 手柄控制

- 按住 `R2` 才允许运动。
- 左摇杆上下控制前进/后退。
- 右摇杆左右控制差速转向。
- 默认速度上限 `V max = 4.0`。

## 测试脚本

```bash
cd /home/jetson/workspace/ros2_ws/src/aiformula/launchers/shellscript
./simple_path_check.sh
```
