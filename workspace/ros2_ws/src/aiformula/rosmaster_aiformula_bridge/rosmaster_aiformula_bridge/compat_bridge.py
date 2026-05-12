from __future__ import annotations

from copy import deepcopy
from typing import Any

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy._rclpy_pybind11 import RCLError
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_msgs.msg import Float32


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _clamp(value: float, limit: float) -> float:
    limit = abs(float(limit))
    return max(-limit, min(limit, float(value)))


class RosmasterAiformulaCompatBridge(Node):
    """Republish ROSMASTER hardware topics using the AI Formula topic contract."""

    def __init__(self) -> None:
        super().__init__("rosmaster_aiformula_compat_bridge")

        self.declare_parameter("input_cmd_vel_topic", "/aiformula_control/game_pad/cmd_vel")
        self.declare_parameter("output_cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("allow_lateral", False)
        self.declare_parameter("max_linear_x", 4.0)
        self.declare_parameter("max_linear_y", 0.0)
        self.declare_parameter("max_angular_z", 4.0)

        self.declare_parameter("input_odom_topic", "/odom_raw")
        self.declare_parameter("output_odom_topic", "/aiformula_sensing/gyro_odometry_publisher/odom")
        self.declare_parameter("output_velocity_body_topic", "/aiformula_sensing/vectornav/velocity_body")
        self.declare_parameter("odom_frame_id", "")
        self.declare_parameter("base_frame_id", "")

        self.declare_parameter("input_imu_topic", "/imu/data")
        self.declare_parameter("output_vectornav_imu_topic", "/aiformula_sensing/vectornav/imu")
        self.declare_parameter("output_zed_imu_topic", "")
        self.declare_parameter("imu_frame_id", "")

        self.declare_parameter("publish_rear_potentiometer_zero", True)
        self.declare_parameter("rear_potentiometer_topic", "/aiformula_sensing/rear_potentiometer/yaw")
        self.declare_parameter("rear_potentiometer_period_sec", 0.1)

        self.input_cmd_vel_topic = str(self.get_parameter("input_cmd_vel_topic").value)
        self.output_cmd_vel_topic = str(self.get_parameter("output_cmd_vel_topic").value)
        self.allow_lateral = _as_bool(self.get_parameter("allow_lateral").value)
        self.max_linear_x = float(self.get_parameter("max_linear_x").value)
        self.max_linear_y = float(self.get_parameter("max_linear_y").value)
        self.max_angular_z = float(self.get_parameter("max_angular_z").value)

        self.input_odom_topic = str(self.get_parameter("input_odom_topic").value)
        self.output_odom_topic = str(self.get_parameter("output_odom_topic").value)
        self.output_velocity_body_topic = str(self.get_parameter("output_velocity_body_topic").value)
        self.odom_frame_id = str(self.get_parameter("odom_frame_id").value)
        self.base_frame_id = str(self.get_parameter("base_frame_id").value)

        self.input_imu_topic = str(self.get_parameter("input_imu_topic").value)
        self.output_vectornav_imu_topic = str(self.get_parameter("output_vectornav_imu_topic").value)
        self.output_zed_imu_topic = str(self.get_parameter("output_zed_imu_topic").value)
        self.imu_frame_id = str(self.get_parameter("imu_frame_id").value)

        self.publish_rear_potentiometer_zero = _as_bool(
            self.get_parameter("publish_rear_potentiometer_zero").value
        )
        self.rear_potentiometer_topic = str(self.get_parameter("rear_potentiometer_topic").value)
        self.rear_potentiometer_period_sec = float(self.get_parameter("rear_potentiometer_period_sec").value)

        self.cmd_pub = self.create_publisher(Twist, self.output_cmd_vel_topic, 10)
        self.cmd_sub = self.create_subscription(Twist, self.input_cmd_vel_topic, self.cmd_vel_callback, 10)

        self.odom_pub = self.create_publisher(Odometry, self.output_odom_topic, 10)
        self.velocity_body_pub = self.create_publisher(Odometry, self.output_velocity_body_topic, 10)
        self.odom_sub = self.create_subscription(Odometry, self.input_odom_topic, self.odom_callback, 10)

        self.vectornav_imu_pub = self.create_publisher(Imu, self.output_vectornav_imu_topic, 10)
        self.zed_imu_pub = None
        if self.output_zed_imu_topic:
            self.zed_imu_pub = self.create_publisher(Imu, self.output_zed_imu_topic, 10)
        self.imu_sub = self.create_subscription(Imu, self.input_imu_topic, self.imu_callback, 10)

        self.rear_potentiometer_pub = None
        self.rear_potentiometer_timer = None
        if self.publish_rear_potentiometer_zero:
            self.rear_potentiometer_pub = self.create_publisher(Float32, self.rear_potentiometer_topic, 10)
            self.rear_potentiometer_timer = self.create_timer(
                self.rear_potentiometer_period_sec, self.rear_potentiometer_callback
            )

        self.get_logger().info(
            f"cmd_vel bridge: {self.input_cmd_vel_topic} -> {self.output_cmd_vel_topic}, "
            f"limits x={self.max_linear_x}, y={self.max_linear_y}, wz={self.max_angular_z}, "
            f"allow_lateral={self.allow_lateral}"
        )
        self.get_logger().info(
            f"odom bridge: {self.input_odom_topic} -> {self.output_odom_topic}, "
            f"velocity_body -> {self.output_velocity_body_topic}"
        )
        self.get_logger().info(f"imu bridge: {self.input_imu_topic} -> {self.output_vectornav_imu_topic}")

    def cmd_vel_callback(self, msg: Twist) -> None:
        bridged = Twist()
        bridged.linear.x = _clamp(msg.linear.x, self.max_linear_x)
        bridged.linear.y = _clamp(msg.linear.y, self.max_linear_y) if self.allow_lateral else 0.0
        bridged.linear.z = 0.0
        bridged.angular.x = 0.0
        bridged.angular.y = 0.0
        bridged.angular.z = _clamp(msg.angular.z, self.max_angular_z)
        self.cmd_pub.publish(bridged)

    def odom_callback(self, msg: Odometry) -> None:
        odom = deepcopy(msg)
        if self.odom_frame_id:
            odom.header.frame_id = self.odom_frame_id
        if self.base_frame_id:
            odom.child_frame_id = self.base_frame_id
        self.odom_pub.publish(odom)

        velocity_body = Odometry()
        velocity_body.header = deepcopy(odom.header)
        velocity_body.child_frame_id = odom.child_frame_id
        velocity_body.twist = deepcopy(odom.twist)
        self.velocity_body_pub.publish(velocity_body)

    def imu_callback(self, msg: Imu) -> None:
        imu = deepcopy(msg)
        if self.imu_frame_id:
            imu.header.frame_id = self.imu_frame_id
        self.vectornav_imu_pub.publish(imu)
        if self.zed_imu_pub is not None:
            self.zed_imu_pub.publish(deepcopy(imu))

    def rear_potentiometer_callback(self) -> None:
        if self.rear_potentiometer_pub is None:
            return
        msg = Float32()
        msg.data = 0.0
        self.rear_potentiometer_pub.publish(msg)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = RosmasterAiformulaCompatBridge()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        try:
            node.destroy_node()
        except (KeyboardInterrupt, RCLError):
            pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
