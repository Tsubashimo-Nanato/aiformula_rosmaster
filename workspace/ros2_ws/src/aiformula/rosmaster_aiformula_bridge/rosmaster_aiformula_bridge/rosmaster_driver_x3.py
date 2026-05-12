from __future__ import annotations

from typing import Any

import rclpy
from geometry_msgs.msg import Twist
from rclpy._rclpy_pybind11 import RCLError
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from sensor_msgs.msg import Imu, MagneticField
from std_msgs.msg import Bool, Float32, Int32, Int32MultiArray

from Rosmaster_Lib import Rosmaster


def _clamp(value: float, limit: float) -> float:
    limit = abs(float(limit))
    return max(-limit, min(limit, float(value)))


def _clamp_motor(value: float) -> int:
    return int(round(max(-100.0, min(100.0, float(value)))))


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


class RosmasterDriverX3(Node):
    """Minimal ROS 2 driver for the Yahboom ROSMASTER base controller."""

    def __init__(self) -> None:
        super().__init__("rosmaster_driver_x3")

        self.declare_parameter("imu_link", "imu_link")
        self.declare_parameter("car_type", 5)
        self.declare_parameter("drive_mode", "rear_motor_diff")
        self.declare_parameter("xlinear_limit", 4.0)
        self.declare_parameter("ylinear_limit", 1.0)
        self.declare_parameter("angular_limit", 4.0)
        self.declare_parameter("wheel_tread", 0.60)
        self.declare_parameter("max_motor_pwm", 100.0)
        self.declare_parameter("left_motor_channel", 4)
        self.declare_parameter("right_motor_channel", 2)
        self.declare_parameter("left_motor_sign", 1.0)
        self.declare_parameter("right_motor_sign", 1.0)
        self.declare_parameter("lock_front_steering", True)
        self.declare_parameter("front_steering_lock_angle", 0.0)
        self.declare_parameter("publish_period_sec", 0.1)
        self.declare_parameter("command_timeout_sec", 0.5)
        self.declare_parameter("enable_led_buzzer_topics", True)

        self.imu_link = str(self.get_parameter("imu_link").value)
        self.car_type = int(self.get_parameter("car_type").value)
        self.drive_mode = str(self.get_parameter("drive_mode").value)
        self.xlinear_limit = float(self.get_parameter("xlinear_limit").value)
        self.ylinear_limit = float(self.get_parameter("ylinear_limit").value)
        self.angular_limit = float(self.get_parameter("angular_limit").value)
        self.wheel_tread = float(self.get_parameter("wheel_tread").value)
        self.max_motor_pwm = abs(float(self.get_parameter("max_motor_pwm").value))
        self.left_motor_channel = int(self.get_parameter("left_motor_channel").value)
        self.right_motor_channel = int(self.get_parameter("right_motor_channel").value)
        self.left_motor_sign = float(self.get_parameter("left_motor_sign").value)
        self.right_motor_sign = float(self.get_parameter("right_motor_sign").value)
        self.lock_front_steering = _as_bool(self.get_parameter("lock_front_steering").value)
        self.front_steering_lock_angle = float(self.get_parameter("front_steering_lock_angle").value)
        self.publish_period_sec = float(self.get_parameter("publish_period_sec").value)
        self.command_timeout_sec = float(self.get_parameter("command_timeout_sec").value)
        self.enable_led_buzzer_topics = _as_bool(self.get_parameter("enable_led_buzzer_topics").value)

        self.car = Rosmaster()
        self.car.set_car_type(self.car_type)
        self.car.create_receive_threading()
        self.lock_front_servos()
        self.last_cmd_time = None
        self.motion_stopped_for_timeout = True
        self.last_reported_twist = Twist()

        self.cmd_sub = self.create_subscription(Twist, "cmd_vel", self.cmd_vel_callback, 10)
        if self.enable_led_buzzer_topics:
            self.rgb_sub = self.create_subscription(Int32, "RGBLight", self.rgb_light_callback, 10)
            self.buzzer_sub = self.create_subscription(Bool, "Buzzer", self.buzzer_callback, 10)

        self.edition_pub = self.create_publisher(Float32, "edition", 10)
        self.voltage_pub = self.create_publisher(Float32, "voltage", 10)
        self.motor_encoder_pub = self.create_publisher(Int32MultiArray, "motor_encoders", 10)
        self.vel_pub = self.create_publisher(Twist, "vel_raw", 50)
        self.imu_pub = self.create_publisher(Imu, "imu/data_raw", 50)
        self.mag_pub = self.create_publisher(MagneticField, "imu/mag", 50)
        self.timer = self.create_timer(self.publish_period_sec, self.publish_data)

        self.get_logger().info(
            "ROSMASTER driver started with "
            f"car_type={self.car_type}, drive_mode={self.drive_mode}, "
            f"limits x={self.xlinear_limit}, y={self.ylinear_limit}, wz={self.angular_limit}"
        )

    def cmd_vel_callback(self, msg: Twist) -> None:
        vx = _clamp(msg.linear.x, self.xlinear_limit)
        wz = _clamp(msg.angular.z, self.angular_limit)
        self.last_cmd_time = self.get_clock().now()
        self.motion_stopped_for_timeout = False
        if self.drive_mode == "rear_motor_diff":
            self.command_rear_motor_diff(vx, wz)
        else:
            vy = _clamp(msg.linear.y, self.ylinear_limit)
            self.car.set_car_motion(vx, vy, wz)
            self.last_reported_twist.linear.x = vx
            self.last_reported_twist.linear.y = vy
            self.last_reported_twist.angular.z = wz

    def command_rear_motor_diff(self, vx: float, wz: float) -> None:
        self.lock_front_servos()
        half_tread = 0.5 * self.wheel_tread
        left_command = _clamp(vx - (wz * half_tread), self.xlinear_limit)
        right_command = _clamp(vx + (wz * half_tread), self.xlinear_limit)
        left_pwm = _clamp_motor(self.left_motor_sign * self.command_to_pwm(left_command))
        right_pwm = _clamp_motor(self.right_motor_sign * self.command_to_pwm(right_command))
        self.set_motor_channels(left_pwm, right_pwm)

        self.last_reported_twist = Twist()
        self.last_reported_twist.linear.x = vx
        self.last_reported_twist.angular.z = wz

    def command_to_pwm(self, command: float) -> float:
        if self.xlinear_limit <= 0.0:
            return 0.0
        return (command / self.xlinear_limit) * self.max_motor_pwm

    def set_motor_channels(self, left_pwm: int, right_pwm: int) -> None:
        speeds = [0, 0, 0, 0]
        if 1 <= self.left_motor_channel <= 4:
            speeds[self.left_motor_channel - 1] = left_pwm
        if 1 <= self.right_motor_channel <= 4:
            speeds[self.right_motor_channel - 1] = right_pwm
        self.car.set_motor(*speeds)

    def lock_front_servos(self) -> None:
        if not self.lock_front_steering:
            return
        self.car.set_akm_steering_angle(int(round(self.front_steering_lock_angle)), False)

    def rgb_light_callback(self, msg: Int32) -> None:
        self.car.set_colorful_effect(int(msg.data), 6, parm=1)

    def buzzer_callback(self, msg: Bool) -> None:
        self.car.set_beep(1 if msg.data else 0)

    def publish_data(self) -> None:
        stamp = self.get_clock().now().to_msg()
        self.lock_front_servos()
        self.stop_if_command_timed_out()

        edition = Float32()
        edition.data = float(self.car.get_version())

        battery = Float32()
        battery.data = float(self.car.get_battery_voltage())

        ax, ay, az = self.car.get_accelerometer_data()
        gx, gy, gz = self.car.get_gyroscope_data()
        mx, my, mz = self.car.get_magnetometer_data()
        vx, vy, wz = self.car.get_motion_data()
        encoders = self.car.get_motor_encoder()

        twist = Twist()
        if self.drive_mode == "rear_motor_diff":
            twist = self.last_reported_twist
        else:
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
        encoder_msg = Int32MultiArray()
        encoder_msg.data = [int(value) for value in encoders]
        self.motor_encoder_pub.publish(encoder_msg)
        self.edition_pub.publish(edition)

    def stop_if_command_timed_out(self) -> None:
        if self.command_timeout_sec <= 0.0 or self.last_cmd_time is None:
            return
        if self.motion_stopped_for_timeout:
            return
        age = self.get_clock().now() - self.last_cmd_time
        if age > Duration(seconds=self.command_timeout_sec):
            self.stop_motion()
            self.motion_stopped_for_timeout = True
            self.get_logger().warn("Command timeout elapsed; sent zero motion.")

    def stop_motion(self) -> None:
        self.set_motor_channels(0, 0)
        self.car.set_car_motion(0.0, 0.0, 0.0)
        self.lock_front_servos()
        self.last_reported_twist = Twist()

    def destroy_node(self) -> bool:
        try:
            self.stop_motion()
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
        try:
            node.destroy_node()
        except (KeyboardInterrupt, RCLError):
            pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
