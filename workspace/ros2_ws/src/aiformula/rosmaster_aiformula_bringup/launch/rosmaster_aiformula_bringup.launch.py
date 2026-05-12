from pathlib import Path

from ament_index_python.packages import get_package_share_directory, get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    yahboom_description_path = get_package_share_path("yahboomcar_description")
    default_model_path = yahboom_description_path / "urdf/yahboomcar_X3.urdf"
    bringup_share = Path(get_package_share_directory("rosmaster_aiformula_bringup"))
    imu_filter_config = str(bringup_share / "config" / "imu_filter_param.yaml")

    model_arg = DeclareLaunchArgument(
        "model",
        default_value=str(default_model_path),
        description="Absolute path to the ROSMASTER X3 URDF file.",
    )
    use_robot_state_publisher_arg = DeclareLaunchArgument(
        "use_robot_state_publisher",
        default_value="true",
        choices=["true", "false"],
        description="Start robot_state_publisher with the ROSMASTER description.",
    )
    use_imu_filter_arg = DeclareLaunchArgument(
        "use_imu_filter",
        default_value="true",
        choices=["true", "false"],
        description="Start imu_filter_madgwick so the bridge can publish oriented IMU messages.",
    )
    pub_odom_tf_arg = DeclareLaunchArgument(
        "pub_odom_tf",
        default_value="false",
        choices=["true", "false"],
        description="Let yahboomcar_base_node publish odom -> base_footprint TF.",
    )
    cmd_input_topic_arg = DeclareLaunchArgument(
        "cmd_input_topic",
        default_value="/aiformula_control/game_pad/cmd_vel",
        description="Sophia-compatible Twist topic to drive ROSMASTER.",
    )
    input_odom_topic_arg = DeclareLaunchArgument(
        "input_odom_topic",
        default_value="/odom_raw",
        description="ROSMASTER odometry topic to republish as Sophia odometry.",
    )
    input_imu_topic_arg = DeclareLaunchArgument(
        "input_imu_topic",
        default_value="/imu/data",
        description="ROSMASTER IMU topic to republish as Sophia VectorNav IMU.",
    )
    allow_lateral_arg = DeclareLaunchArgument(
        "allow_lateral",
        default_value="false",
        choices=["true", "false"],
        description="Allow AI Formula commands to use ROSMASTER mecanum lateral velocity.",
    )
    max_linear_x_arg = DeclareLaunchArgument(
        "max_linear_x",
        default_value="0.35",
        description="Conservative forward velocity limit for first tests.",
    )
    max_linear_y_arg = DeclareLaunchArgument(
        "max_linear_y",
        default_value="0.0",
        description="Conservative lateral velocity limit. Ignored when allow_lateral is false.",
    )
    max_angular_z_arg = DeclareLaunchArgument(
        "max_angular_z",
        default_value="0.8",
        description="Conservative yaw velocity limit for first tests.",
    )
    suppress_buzzer_arg = DeclareLaunchArgument(
        "suppress_buzzer",
        default_value="true",
        choices=["true", "false"],
        description="Continuously send buzzer-off while the ROSMASTER driver is running.",
    )

    robot_description = ParameterValue(
        Command(["xacro ", LaunchConfiguration("model")]),
        value_type=str,
    )

    robot_state_publisher_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        parameters=[{"robot_description": robot_description}],
        condition=IfCondition(LaunchConfiguration("use_robot_state_publisher")),
    )

    driver_node = Node(
        package="rosmaster_aiformula_bridge",
        executable="rosmaster_driver_x3",
        name="rosmaster_driver",
        output="screen",
        parameters=[
            {
                "suppress_buzzer": ParameterValue(LaunchConfiguration("suppress_buzzer"), value_type=bool),
            }
        ],
        remappings=[
            ("cmd_vel", "/cmd_vel"),
        ],
    )

    base_node = Node(
        package="yahboomcar_base_node",
        executable="base_node_X3",
        name="rosmaster_base_node",
        output="screen",
        parameters=[
            {
                "pub_odom_tf": ParameterValue(LaunchConfiguration("pub_odom_tf"), value_type=bool),
                "linear_scale_x": 1.0,
                "linear_scale_y": 1.0,
                "angular_scale": 1.0,
                "odom_frame": "odom",
                "base_footprint_frame": "base_footprint",
            }
        ],
    )

    imu_filter_node = Node(
        package="imu_filter_madgwick",
        executable="imu_filter_madgwick_node",
        name="imu_filter_madgwick",
        output="screen",
        parameters=[imu_filter_config],
        condition=IfCondition(LaunchConfiguration("use_imu_filter")),
    )

    compat_bridge_node = Node(
        package="rosmaster_aiformula_bridge",
        executable="compat_bridge",
        name="rosmaster_aiformula_compat_bridge",
        output="screen",
        parameters=[
            {
                "input_cmd_vel_topic": LaunchConfiguration("cmd_input_topic"),
                "output_cmd_vel_topic": "/cmd_vel",
                "allow_lateral": ParameterValue(LaunchConfiguration("allow_lateral"), value_type=bool),
                "max_linear_x": ParameterValue(LaunchConfiguration("max_linear_x"), value_type=float),
                "max_linear_y": ParameterValue(LaunchConfiguration("max_linear_y"), value_type=float),
                "max_angular_z": ParameterValue(LaunchConfiguration("max_angular_z"), value_type=float),
                "input_odom_topic": LaunchConfiguration("input_odom_topic"),
                "output_odom_topic": "/aiformula_sensing/gyro_odometry_publisher/odom",
                "output_velocity_body_topic": "/aiformula_sensing/vectornav/velocity_body",
                "odom_frame_id": "odom",
                "base_frame_id": "base_footprint",
                "input_imu_topic": LaunchConfiguration("input_imu_topic"),
                "output_vectornav_imu_topic": "/aiformula_sensing/vectornav/imu",
                "output_zed_imu_topic": "",
                "imu_frame_id": "imu_link",
                "publish_rear_potentiometer_zero": True,
                "rear_potentiometer_topic": "/aiformula_sensing/rear_potentiometer/yaw",
                "rear_potentiometer_period_sec": 0.1,
            }
        ],
    )

    return LaunchDescription(
        [
            model_arg,
            use_robot_state_publisher_arg,
            use_imu_filter_arg,
            pub_odom_tf_arg,
            cmd_input_topic_arg,
            input_odom_topic_arg,
            input_imu_topic_arg,
            allow_lateral_arg,
            max_linear_x_arg,
            max_linear_y_arg,
            max_angular_z_arg,
            suppress_buzzer_arg,
            robot_state_publisher_node,
            driver_node,
            base_node,
            imu_filter_node,
            compat_bridge_node,
        ]
    )
