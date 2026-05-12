from __future__ import annotations

from copy import deepcopy
from typing import Any

import rclpy
from rclpy._rclpy_pybind11 import RCLError
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image, PointCloud2


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


class RosmasterCameraCompatBridge(Node):
    """Expose ROSMASTER USB/Orbbec camera streams using AI Formula ZED topic names."""

    def __init__(self) -> None:
        super().__init__("rosmaster_camera_compat_bridge")

        self.declare_parameter("input_color_image_topic", "/usb_cam/image_raw")
        self.declare_parameter("input_color_camera_info_topic", "/usb_cam/camera_info")
        self.declare_parameter("input_depth_image_topic", "/camera/depth/image_raw")
        self.declare_parameter("input_depth_camera_info_topic", "/camera/depth/camera_info")
        self.declare_parameter("input_point_cloud_topic", "/camera/depth/points")

        self.declare_parameter("output_left_image_topic", "/aiformula_sensing/zed_node/left_image/undistorted")
        self.declare_parameter("output_right_image_topic", "/aiformula_sensing/zed_node/right_image/undistorted")
        self.declare_parameter("output_left_camera_info_topic", "/aiformula_sensing/zed_node/left/camera_info")
        self.declare_parameter("output_right_camera_info_topic", "/aiformula_sensing/zed_node/right/camera_info")
        self.declare_parameter("output_depth_image_topic", "/aiformula_sensing/zed_node/depth/depth_registered")
        self.declare_parameter("output_depth_camera_info_topic", "/aiformula_sensing/zed_node/depth/camera_info")
        self.declare_parameter("output_point_cloud_topic", "/aiformula_sensing/zed_node/point_cloud/cloud_registered")

        self.declare_parameter("left_frame_id", "zed_left_camera_optical_frame")
        self.declare_parameter("right_frame_id", "zed_right_camera_optical_frame")
        self.declare_parameter("depth_frame_id", "zed_left_camera_optical_frame")
        self.declare_parameter("point_cloud_frame_id", "zed_left_camera_optical_frame")
        self.declare_parameter("publish_right_image_copy", True)
        self.declare_parameter("publish_depth", True)
        self.declare_parameter("publish_point_cloud", True)

        self.input_color_image_topic = str(self.get_parameter("input_color_image_topic").value)
        self.input_color_camera_info_topic = str(self.get_parameter("input_color_camera_info_topic").value)
        self.input_depth_image_topic = str(self.get_parameter("input_depth_image_topic").value)
        self.input_depth_camera_info_topic = str(self.get_parameter("input_depth_camera_info_topic").value)
        self.input_point_cloud_topic = str(self.get_parameter("input_point_cloud_topic").value)

        self.output_left_image_topic = str(self.get_parameter("output_left_image_topic").value)
        self.output_right_image_topic = str(self.get_parameter("output_right_image_topic").value)
        self.output_left_camera_info_topic = str(self.get_parameter("output_left_camera_info_topic").value)
        self.output_right_camera_info_topic = str(self.get_parameter("output_right_camera_info_topic").value)
        self.output_depth_image_topic = str(self.get_parameter("output_depth_image_topic").value)
        self.output_depth_camera_info_topic = str(self.get_parameter("output_depth_camera_info_topic").value)
        self.output_point_cloud_topic = str(self.get_parameter("output_point_cloud_topic").value)

        self.left_frame_id = str(self.get_parameter("left_frame_id").value)
        self.right_frame_id = str(self.get_parameter("right_frame_id").value)
        self.depth_frame_id = str(self.get_parameter("depth_frame_id").value)
        self.point_cloud_frame_id = str(self.get_parameter("point_cloud_frame_id").value)
        self.publish_right_image_copy = _as_bool(self.get_parameter("publish_right_image_copy").value)
        self.publish_depth = _as_bool(self.get_parameter("publish_depth").value)
        self.publish_point_cloud = _as_bool(self.get_parameter("publish_point_cloud").value)

        self.left_image_pub = self.create_publisher(Image, self.output_left_image_topic, 10)
        self.right_image_pub = None
        if self.publish_right_image_copy:
            self.right_image_pub = self.create_publisher(Image, self.output_right_image_topic, 10)
        self.left_camera_info_pub = self.create_publisher(CameraInfo, self.output_left_camera_info_topic, 10)
        self.right_camera_info_pub = None
        if self.publish_right_image_copy:
            self.right_camera_info_pub = self.create_publisher(CameraInfo, self.output_right_camera_info_topic, 10)

        self.depth_image_pub = None
        self.depth_camera_info_pub = None
        if self.publish_depth:
            self.depth_image_pub = self.create_publisher(Image, self.output_depth_image_topic, 10)
            self.depth_camera_info_pub = self.create_publisher(CameraInfo, self.output_depth_camera_info_topic, 10)

        self.point_cloud_pub = None
        if self.publish_point_cloud:
            self.point_cloud_pub = self.create_publisher(PointCloud2, self.output_point_cloud_topic, 10)

        self.create_subscription(Image, self.input_color_image_topic, self.color_image_callback, qos_profile_sensor_data)
        self.create_subscription(
            CameraInfo, self.input_color_camera_info_topic, self.color_camera_info_callback, qos_profile_sensor_data
        )
        if self.publish_depth:
            self.create_subscription(Image, self.input_depth_image_topic, self.depth_image_callback, qos_profile_sensor_data)
            self.create_subscription(
                CameraInfo,
                self.input_depth_camera_info_topic,
                self.depth_camera_info_callback,
                qos_profile_sensor_data,
            )
        if self.publish_point_cloud:
            self.create_subscription(
                PointCloud2, self.input_point_cloud_topic, self.point_cloud_callback, qos_profile_sensor_data
            )

        self.get_logger().info(
            f"camera bridge: {self.input_color_image_topic} -> {self.output_left_image_topic}"
        )
        if self.publish_right_image_copy:
            self.get_logger().warn(
                f"publishing {self.output_right_image_topic} as a copy of the monocular ROSMASTER USB camera"
            )
        if self.publish_point_cloud:
            self.get_logger().info(
                f"point cloud bridge: {self.input_point_cloud_topic} -> {self.output_point_cloud_topic}"
            )

    def color_image_callback(self, msg: Image) -> None:
        left = deepcopy(msg)
        left.header.frame_id = self.left_frame_id
        self.left_image_pub.publish(left)

        if self.right_image_pub is not None:
            right = deepcopy(msg)
            right.header.frame_id = self.right_frame_id
            self.right_image_pub.publish(right)

    def color_camera_info_callback(self, msg: CameraInfo) -> None:
        left = deepcopy(msg)
        left.header.frame_id = self.left_frame_id
        self.left_camera_info_pub.publish(left)

        if self.right_camera_info_pub is not None:
            right = deepcopy(msg)
            right.header.frame_id = self.right_frame_id
            self.right_camera_info_pub.publish(right)

    def depth_image_callback(self, msg: Image) -> None:
        if self.depth_image_pub is None:
            return
        depth = deepcopy(msg)
        depth.header.frame_id = self.depth_frame_id
        self.depth_image_pub.publish(depth)

    def depth_camera_info_callback(self, msg: CameraInfo) -> None:
        if self.depth_camera_info_pub is None:
            return
        info = deepcopy(msg)
        info.header.frame_id = self.depth_frame_id
        self.depth_camera_info_pub.publish(info)

    def point_cloud_callback(self, msg: PointCloud2) -> None:
        if self.point_cloud_pub is None:
            return
        cloud = deepcopy(msg)
        cloud.header.frame_id = self.point_cloud_frame_id
        self.point_cloud_pub.publish(cloud)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = RosmasterCameraCompatBridge()
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
