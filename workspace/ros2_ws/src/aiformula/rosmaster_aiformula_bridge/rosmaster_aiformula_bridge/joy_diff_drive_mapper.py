from __future__ import annotations

from typing import Any, Sequence

import rclpy
from geometry_msgs.msg import Twist
from rclpy._rclpy_pybind11 import RCLError
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Joy


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _axis(values: Sequence[float], index: int) -> float:
    if index < 0 or index >= len(values):
        return 0.0
    return float(values[index])


def _button(values: Sequence[int], index: int) -> bool:
    return 0 <= index < len(values) and int(values[index]) != 0


def _deadzone(value: float, threshold: float) -> float:
    return 0.0 if abs(value) < abs(threshold) else value


class JoyDiffDriveMapper(Node):
    """Map a USB gamepad to the AI Formula differential-drive cmd_vel topic."""

    def __init__(self) -> None:
        super().__init__("joy_diff_drive_mapper")

        self.declare_parameter("cmd_vel_topic", "/aiformula_control/game_pad/cmd_vel")
        self.declare_parameter("linear_axis", 1)
        self.declare_parameter("angular_axis", 2)
        self.declare_parameter("linear_axis_sign", 1.0)
        self.declare_parameter("angular_axis_sign", 1.0)
        self.declare_parameter("enable_button", 7)
        self.declare_parameter("enable_axis", 5)
        self.declare_parameter("enable_axis_threshold", -0.5)
        self.declare_parameter("require_enable", True)
        self.declare_parameter("deadzone", 0.12)
        self.declare_parameter("max_linear_x", 4.0)
        self.declare_parameter("max_angular_z", 4.0)
        self.declare_parameter("publish_rate_hz", 20.0)
        self.declare_parameter("joy_timeout_sec", 0.35)

        self.cmd_vel_topic = str(self.get_parameter("cmd_vel_topic").value)
        self.linear_axis = int(self.get_parameter("linear_axis").value)
        self.angular_axis = int(self.get_parameter("angular_axis").value)
        self.linear_axis_sign = float(self.get_parameter("linear_axis_sign").value)
        self.angular_axis_sign = float(self.get_parameter("angular_axis_sign").value)
        self.enable_button = int(self.get_parameter("enable_button").value)
        self.enable_axis = int(self.get_parameter("enable_axis").value)
        self.enable_axis_threshold = float(self.get_parameter("enable_axis_threshold").value)
        self.require_enable = _as_bool(self.get_parameter("require_enable").value)
        self.deadzone = float(self.get_parameter("deadzone").value)
        self.max_linear_x = abs(float(self.get_parameter("max_linear_x").value))
        self.max_angular_z = abs(float(self.get_parameter("max_angular_z").value))
        self.joy_timeout = float(self.get_parameter("joy_timeout_sec").value)
        publish_rate_hz = max(1.0, float(self.get_parameter("publish_rate_hz").value))

        self.cmd_pub = self.create_publisher(Twist, self.cmd_vel_topic, 10)
        self.joy_sub = self.create_subscription(Joy, "joy", self.joy_callback, 10)
        self.timer = self.create_timer(1.0 / publish_rate_hz, self.publish_latest)

        self.last_joy_time = None
        self.latest_twist = Twist()
        self.enabled = False
        self.last_publish_was_zero = False

        self.get_logger().info(
            "Joystick differential-drive mapper started: "
            f"R2 button={self.enable_button}, R2 axis={self.enable_axis}, "
            f"linear axis={self.linear_axis}, angular axis={self.angular_axis}, "
            f"cmd_vel={self.cmd_vel_topic}"
        )

    def joy_callback(self, msg: Joy) -> None:
        self.last_joy_time = self.get_clock().now()

        button_enabled = _button(msg.buttons, self.enable_button)
        axis_value = _axis(msg.axes, self.enable_axis)
        axis_enabled = axis_value <= self.enable_axis_threshold
        self.enabled = (not self.require_enable) or button_enabled or axis_enabled

        twist = Twist()
        if self.enabled:
            linear = _deadzone(_axis(msg.axes, self.linear_axis), self.deadzone)
            angular = _deadzone(_axis(msg.axes, self.angular_axis), self.deadzone)
            twist.linear.x = self.linear_axis_sign * linear * self.max_linear_x
            twist.angular.z = self.angular_axis_sign * angular * self.max_angular_z

        self.latest_twist = twist
        self.publish_twist(twist)

    def publish_latest(self) -> None:
        if self.last_joy_time is None:
            self.publish_zero_once()
            return

        age = self.get_clock().now() - self.last_joy_time
        if self.joy_timeout > 0.0 and age > Duration(seconds=self.joy_timeout):
            self.enabled = False
            self.latest_twist = Twist()
            self.publish_zero_once()
            return

        if self.enabled:
            self.publish_twist(self.latest_twist)
        else:
            self.publish_zero_once()

    def publish_twist(self, twist: Twist) -> None:
        self.cmd_pub.publish(twist)
        self.last_publish_was_zero = (
            twist.linear.x == 0.0
            and twist.linear.y == 0.0
            and twist.linear.z == 0.0
            and twist.angular.x == 0.0
            and twist.angular.y == 0.0
            and twist.angular.z == 0.0
        )

    def publish_zero_once(self) -> None:
        if not self.last_publish_was_zero:
            self.publish_twist(Twist())

    def destroy_node(self) -> bool:
        if rclpy.ok():
            for _ in range(3):
                try:
                    self.cmd_pub.publish(Twist())
                except RCLError:
                    break
        return super().destroy_node()


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = JoyDiffDriveMapper()
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
