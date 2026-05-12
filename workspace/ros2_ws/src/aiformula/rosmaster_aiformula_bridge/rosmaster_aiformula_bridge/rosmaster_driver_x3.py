from __future__ import annotations

from typing import Any

import rclpy
from geometry_msgs.msg import Twist
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Imu, MagneticField
from std_msgs.msg import Bool, Float32, Int32

from Rosmaster_Lib import Rosmaster


def _clamp(value: float, limit: float) -> float:
    limit = abs(float(limit))
    return max(-limit, min(limit, float(value)))


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


class RosmasterDriverX3(Node):
    """Minimal ROS 2 driver for the Yahboom ROSMASTER X3 base."""

    def __init__(self) -> None:
        super().__init__("rosmaster_driver_x3")

        self.declare_parameter("imu_link", "imu_link")
        self.declare_parameter("xlinear_limit", 1.0)
        self.declare_parameter("ylinear_limit", 1.0)
        self.declare_parameter("angular_limit", 5.0)
        self.declare_parameter("publish_period_sec", 0.1)
        self.declare_parameter("enable_led_buzzer_topics", True)
        self.declare_parameter("suppress_buzzer", True)

        self.imu_link = str(self.get_parameter("imu_link").value)
        self.xlinear_limit = float(self.get_parameter("xlinear_limit").value)
        self.ylinear_limit = float(self.get_parameter("ylinear_limit").value)
        self.angular_limit = float(self.get_parameter("angular_limit").value)
        self.publish_period_sec = float(self.get_parameter("publish_period_sec").value)
        self.enable_led_buzzer_topics = _as_bool(self.get_parameter("enable_led_buzzer_topics").value)
        self.suppress_buzzer = _as_bool(self.get_parameter("suppress_buzzer").value)

        self.car = Rosmaster()
        self.car.set_car_type(1)
        self.car.create_receive_threading()

        self.cmd_sub = self.create_subscription(Twist, "cmd_vel", self.cmd_vel_callback, 10)
        if self.enable_led_buzzer_topics:
            self.rgb_sub = self.create_subscription(Int32, "RGBLight", self.rgb_light_callback, 10)
            self.buzzer_sub = self.create_subscription(Bool, "Buzzer", self.buzzer_callback, 10)

        self.edition_pub = self.create_publisher(Float32, "edition", 10)
        self.voltage_pub = self.create_publisher(Float32, "voltage", 10)
        self.vel_pub = self.create_publisher(Twist, "vel_raw", 50)
        self.imu_pub = self.create_publisher(Imu, "imu/data_raw", 50)
        self.mag_pub = self.create_publisher(MagneticField, "imu/mag", 50)
        self.timer = self.create_timer(self.publish_period_sec, self.publish_data)

        self.get_logger().info(
            "ROSMASTER X3 driver started with limits "
            f"x={self.xlinear_limit}, y={self.ylinear_limit}, wz={self.angular_limit}"
        )
        if self.suppress_buzzer:
            self.get_logger().warn("Buzzer suppression is enabled. Charge the robot battery if the buzzer keeps returning.")

    def cmd_vel_callback(self, msg: Twist) -> None:
        vx = _clamp(msg.linear.x, self.xlinear_limit)
        vy = _clamp(msg.linear.y, self.ylinear_limit)
        wz = _clamp(msg.angular.z, self.angular_limit)
        self.car.set_car_motion(vx, vy, wz)

    def rgb_light_callback(self, msg: Int32) -> None:
        self.car.set_colorful_effect(int(msg.data), 6, parm=1)

    def buzzer_callback(self, msg: Bool) -> None:
        self.car.set_beep(1 if msg.data else 0)

    def publish_data(self) -> None:
        stamp = self.get_clock().now().to_msg()
        if self.suppress_buzzer:
            self.car.set_beep(0)

        edition = Float32()
        edition.data = float(self.car.get_version())

        battery = Float32()
        battery.data = float(self.car.get_battery_voltage())

        ax, ay, az = self.car.get_accelerometer_data()
        gx, gy, gz = self.car.get_gyroscope_data()
        mx, my, mz = self.car.get_magnetometer_data()
        vx, vy, wz = self.car.get_motion_data()

        twist = Twist()
        twist.linear.x = float(vx)
        twist.linear.y = float(vy)
        twist.angular.z = float(wz)

        imu = Imu()
        imu.header.stamp = stamp
        imu.header.frame_id = self.imu_link
        imu.linear_acceleration.x = float(ax)
        imu.linear_acceleration.y = float(ay)
        imu.linear_acceleration.z = float(az)
        imu.angular_velocity.x = float(gx)
        imu.angular_velocity.y = float(gy)
        imu.angular_velocity.z = float(gz)
        imu.orientation_covariance[0] = -1.0

        mag = MagneticField()
        mag.header.stamp = stamp
        mag.header.frame_id = self.imu_link
        mag.magnetic_field.x = float(mx)
        mag.magnetic_field.y = float(my)
        mag.magnetic_field.z = float(mz)

        self.vel_pub.publish(twist)
        self.imu_pub.publish(imu)
        self.mag_pub.publish(mag)
        self.voltage_pub.publish(battery)
        self.edition_pub.publish(edition)

    def destroy_node(self) -> bool:
        try:
            self.car.set_car_motion(0.0, 0.0, 0.0)
            self.car.set_beep(0)
        except Exception as exc:
            self.get_logger().warn(f"Failed to send final stop command: {exc!r}")
        return super().destroy_node()


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = RosmasterDriverX3()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
