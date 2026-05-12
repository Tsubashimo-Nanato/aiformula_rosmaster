from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    rosmaster_bringup_dir = get_package_share_directory("rosmaster_aiformula_bringup")
    yahboom_description_dir = Path(get_package_share_directory("yahboomcar_description"))
    default_rviz_config = yahboom_description_dir / "rviz" / "yahboomcar.rviz"

    use_rviz_arg = DeclareLaunchArgument(
        "use_rviz",
        default_value="true",
        choices=["true", "false"],
        description="Start RViz with the ROSMASTER model view.",
    )
    allow_lateral_arg = DeclareLaunchArgument(
        "allow_lateral",
        default_value="false",
        choices=["true", "false"],
        description="Allow lateral mecanum motion from AI Formula cmd_vel.",
    )
    max_linear_x_arg = DeclareLaunchArgument(
        "max_linear_x",
        default_value="0.35",
        description="Forward velocity limit passed to the ROSMASTER compatibility bridge.",
    )
    max_linear_y_arg = DeclareLaunchArgument(
        "max_linear_y",
        default_value="0.0",
        description="Lateral velocity limit passed to the ROSMASTER compatibility bridge.",
    )
    max_angular_z_arg = DeclareLaunchArgument(
        "max_angular_z",
        default_value="0.8",
        description="Yaw velocity limit passed to the ROSMASTER compatibility bridge.",
    )
    suppress_buzzer_arg = DeclareLaunchArgument(
        "suppress_buzzer",
        default_value="true",
        choices=["true", "false"],
        description="Continuously send buzzer-off while the ROSMASTER driver is running.",
    )
    use_joy_arg = DeclareLaunchArgument(
        "use_joy",
        default_value="true",
        choices=["true", "false"],
        description="Start USB gamepad control through the AI Formula cmd_vel topic.",
    )

    rosmaster_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            str(Path(rosmaster_bringup_dir) / "launch" / "rosmaster_aiformula_bringup.launch.py")
        ),
        launch_arguments={
            "allow_lateral": LaunchConfiguration("allow_lateral"),
            "max_linear_x": LaunchConfiguration("max_linear_x"),
            "max_linear_y": LaunchConfiguration("max_linear_y"),
            "max_angular_z": LaunchConfiguration("max_angular_z"),
            "suppress_buzzer": LaunchConfiguration("suppress_buzzer"),
            "use_joy": LaunchConfiguration("use_joy"),
        }.items(),
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", str(default_rviz_config)],
        condition=IfCondition(LaunchConfiguration("use_rviz")),
    )

    return LaunchDescription(
        [
            use_rviz_arg,
            allow_lateral_arg,
            max_linear_x_arg,
            max_linear_y_arg,
            max_angular_z_arg,
            suppress_buzzer_arg,
            use_joy_arg,
            rosmaster_bringup,
            rviz,
        ]
    )
