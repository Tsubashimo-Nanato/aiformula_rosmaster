from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    share_dir = Path(get_package_share_directory("road_detector"))

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "onnx_path",
                default_value=str(share_dir / "weights" / "yolop-epoch-240-640.onnx"),
                description="Path to the YOLOP_A1 lane-only ONNX model.",
            ),
            DeclareLaunchArgument(
                "input_image_topic",
                default_value="/aiformula_sensing/zed_node/left_image/undistorted",
                description="Input RGB camera topic.",
            ),
            DeclareLaunchArgument(
                "mask_image_topic",
                default_value="/aiformula_perception/road_detector/mask_image",
                description="Output mono8 lane mask topic expected by the AI Formula stack.",
            ),
            DeclareLaunchArgument(
                "mask_roi_topic",
                default_value="/aiformula_perception/road_detector/mask_image_roi",
                description="Output mono8 ROI lane mask topic.",
            ),
            DeclareLaunchArgument(
                "annotated_mask_image_topic",
                default_value="/aiformula_visualization/road_detector/annotated_mask_image",
                description="Output BGR debug overlay topic.",
            ),
            DeclareLaunchArgument(
                "provider",
                default_value="cuda",
                choices=["auto", "tensorrt", "cuda", "cpu"],
                description="ONNX Runtime provider preference.",
            ),
            DeclareLaunchArgument(
                "input_size",
                default_value="640",
                description="Square YOLOP model input size.",
            ),
            DeclareLaunchArgument(
                "ll_threshold",
                default_value="0.5",
                description="Threshold used only for single-channel lane outputs.",
            ),
            DeclareLaunchArgument(
                "drop_every_n",
                default_value="2",
                description="Process every Nth frame. 1 means every frame.",
            ),
            DeclareLaunchArgument(
                "publish_annotated",
                default_value="true",
                choices=["true", "false"],
                description="Publish debug overlay images.",
            ),
            Node(
                package="road_detector",
                executable="road_detector",
                name="road_detector",
                namespace="/aiformula_perception",
                output="screen",
                parameters=[
                    str(share_dir / "config" / "yolop_a1.yaml"),
                    {
                        "onnx_path": LaunchConfiguration("onnx_path"),
                        "provider": LaunchConfiguration("provider"),
                        "input_size": ParameterValue(LaunchConfiguration("input_size"), value_type=int),
                        "ll_threshold": ParameterValue(LaunchConfiguration("ll_threshold"), value_type=float),
                        "drop_every_n": ParameterValue(LaunchConfiguration("drop_every_n"), value_type=int),
                        "publish_annotated": ParameterValue(
                            LaunchConfiguration("publish_annotated"), value_type=bool
                        ),
                    },
                ],
                remappings=[
                    ("sub_image", LaunchConfiguration("input_image_topic")),
                    ("pub_mask_image", LaunchConfiguration("mask_image_topic")),
                    ("pub_mask_image_roi", LaunchConfiguration("mask_roi_topic")),
                    ("pub_annotated_mask_image", LaunchConfiguration("annotated_mask_image_topic")),
                ],
            ),
        ]
    )
