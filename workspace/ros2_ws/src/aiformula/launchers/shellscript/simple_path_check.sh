#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/source_rosmaster_env.sh"

python3 - <<'PY'
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_msgs.msg import Float32, Int32MultiArray


class SimplePathCheck(Node):
    def __init__(self):
        super().__init__("simple_path_check")
        self.cmd_pub = self.create_publisher(Twist, "/aiformula_control/game_pad/cmd_vel", 10)
        self.voltage = None
        self.imu = None
        self.encoders = None
        self.odom = None
        self.create_subscription(Float32, "/voltage", self.voltage_callback, 10)
        self.create_subscription(Imu, "/imu/data_raw", self.imu_callback, 10)
        self.create_subscription(Int32MultiArray, "/motor_encoders", self.encoder_callback, 10)
        self.create_subscription(Odometry, "/aiformula_sensing/gyro_odometry_publisher/odom", self.odom_callback, 10)

    def voltage_callback(self, msg):
        self.voltage = float(msg.data)

    def imu_callback(self, msg):
        self.imu = msg

    def encoder_callback(self, msg):
        self.encoders = list(msg.data)

    def odom_callback(self, msg):
        self.odom = msg

    def wait_for_samples(self, seconds=2.0):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.05)
            if self.voltage is not None and self.imu is not None and self.encoders is not None:
                return

    def publish_for(self, seconds, vx, wz, rate_hz=20.0):
        msg = Twist()
        msg.linear.x = float(vx)
        msg.angular.z = float(wz)
        period = 1.0 / rate_hz
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.cmd_pub.publish(msg)
            rclpy.spin_once(self, timeout_sec=0.0)
            time.sleep(period)

    def stop(self):
        self.publish_for(0.4, 0.0, 0.0)


def main():
    rclpy.init()
    node = SimplePathCheck()
    try:
        node.wait_for_samples()
        before = node.encoders[:] if node.encoders is not None else None
        print("[simple_path_check] voltage:", node.voltage)
        if node.imu is not None:
            acc = node.imu.linear_acceleration
            gyro = node.imu.angular_velocity
            print(
                "[simple_path_check] imu:",
                f"acc=({acc.x:.3f}, {acc.y:.3f}, {acc.z:.3f})",
                f"gyro=({gyro.x:.3f}, {gyro.y:.3f}, {gyro.z:.3f})",
            )
        print("[simple_path_check] encoders before:", before)

        print("[simple_path_check] running path: forward, yaw, reverse")
        node.publish_for(1.0, 1.20, 0.00)
        node.stop()
        node.publish_for(0.8, 0.00, 1.20)
        node.stop()
        node.publish_for(0.8, -1.00, 0.00)
        node.stop()
        node.wait_for_samples()

        after = node.encoders[:] if node.encoders is not None else None
        print("[simple_path_check] encoders after:", after)
        if before is not None and after is not None and len(before) == len(after):
            print("[simple_path_check] encoder delta:", [a - b for a, b in zip(after, before)])
        if node.odom is not None:
            twist = node.odom.twist.twist
            print(
                "[simple_path_check] odom twist:",
                f"linear.x={twist.linear.x:.3f}",
                f"angular.z={twist.angular.z:.3f}",
            )
        print("[simple_path_check] complete")
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
PY
