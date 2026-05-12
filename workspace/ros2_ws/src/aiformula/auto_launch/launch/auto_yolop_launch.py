from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    road_detector_launch = Path(get_package_share_directory("road_detector")) / "launch" / "road_detector.launch.py"

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "input_image_topic",
                default_value="/aiformula_sensing/zed_node/left_image/undistorted",
                description="Input RGB image topic for YOLOP.",
            ),
            DeclareLaunchArgument(
                "mask_image_topic",
                default_value="/aiformula_perception/road_detector/mask_image",
                description="Output mono8 YOLOP lane mask topic.",
            ),
            DeclareLaunchArgument(
                "provider",
                default_value="cuda",
                choices=["auto", "tensorrt", "cuda", "cpu"],
                description="ONNX Runtime provider preference.",
            ),
            DeclareLaunchArgument(
                "drop_every_n",
                default_value="2",
                description="Process every Nth frame.",
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(str(road_detector_launch)),
                launch_arguments={
                    "input_image_topic": LaunchConfiguration("input_image_topic"),
                    "mask_image_topic": LaunchConfiguration("mask_image_topic"),
                    "provider": LaunchConfiguration("provider"),
                    "drop_every_n": LaunchConfiguration("drop_every_n"),
                }.items(),
            ),
        ]
    )
