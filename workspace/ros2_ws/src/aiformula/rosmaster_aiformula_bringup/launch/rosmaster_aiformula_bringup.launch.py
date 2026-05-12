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
    default_model_path = yahboom_description_path / "urdf/yahboomcar_R2.urdf.xacro"
    bringup_share = Path(get_package_share_directory("rosmaster_aiformula_bringup"))
    imu_filter_config = str(bringup_share / "config" / "imu_filter_param.yaml")

    model_arg = DeclareLaunchArgument(
        "model",
        default_value=str(default_model_path),
        description="Absolute path to the ROSMASTER R2 URDF file.",
    )
    car_type_arg = DeclareLaunchArgument(
        "car_type",
        default_value="5",
        description="Rosmaster_Lib car type. Yahboom R2/R2L is 5.",
    )
    drive_mode_arg = DeclareLaunchArgument(
        "drive_mode",
        default_value="rear_motor_diff",
        choices=["rear_motor_diff", "car_motion"],
        description="Use rear motors as differential drive, or pass cmd_vel through set_car_motion.",
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
        description="Allow lateral velocity. Keep false while front steering is locked.",
    )
    max_linear_x_arg = DeclareLaunchArgument(
        "max_linear_x",
        default_value="4.0",
        description="Forward velocity command limit.",
    )
    max_linear_y_arg = DeclareLaunchArgument(
        "max_linear_y",
        default_value="0.0",
        description="Conservative lateral velocity limit. Ignored when allow_lateral is false.",
    )
    max_angular_z_arg = DeclareLaunchArgument(
        "max_angular_z",
        default_value="4.0",
        description="Yaw command limit.",
    )
    command_timeout_arg = DeclareLaunchArgument(
        "command_timeout_sec",
        default_value="0.5",
        description="Stop the base if no cmd_vel arrives within this many seconds.",
    )
    use_joy_arg = DeclareLaunchArgument(
        "use_joy",
        default_value="true",
        choices=["true", "false"],
        description="Start USB gamepad control through the AI Formula cmd_vel topic.",
    )
    joy_device_id_arg = DeclareLaunchArgument(
        "joy_device_id",
        default_value="0",
        description="Linux joystick device id used by joy_node.",
    )
    joy_deadzone_arg = DeclareLaunchArgument(
        "joy_deadzone",
        default_value="0.12",
        description="Deadzone for joystick axes.",
    )
    joy_enable_button_arg = DeclareLaunchArgument(
        "joy_enable_button",
        default_value="7",
        description="Button index used as the R2 deadman when the controller exposes R2 as a button.",
    )
    joy_enable_axis_arg = DeclareLaunchArgument(
        "joy_enable_axis",
        default_value="5",
        description="Axis index used as the R2 deadman when the controller exposes R2 as an analog trigger.",
    )
    joy_linear_axis_arg = DeclareLaunchArgument(
        "joy_linear_axis",
        default_value="1",
        description="Left-stick vertical axis for forward/back motion.",
    )
    joy_angular_axis_arg = DeclareLaunchArgument(
        "joy_angular_axis",
        default_value="2",
        description="Right-stick horizontal axis for differential-drive yaw.",
    )
    joy_max_linear_x_arg = DeclareLaunchArgument(
        "joy_max_linear_x",
        default_value="4.0",
        description="Maximum joystick forward command.",
    )
    joy_max_angular_z_arg = DeclareLaunchArgument(
        "joy_max_angular_z",
        default_value="4.0",
        description="Maximum joystick yaw command.",
    )
    max_motor_pwm_arg = DeclareLaunchArgument(
        "max_motor_pwm",
        default_value="100.0",
        description="Rear motor PWM used at max command.",
    )
    left_motor_channel_arg = DeclareLaunchArgument(
        "left_motor_channel",
        default_value="4",
        description="Rosmaster_Lib set_motor channel for the left rear motor.",
    )
    right_motor_channel_arg = DeclareLaunchArgument(
        "right_motor_channel",
        default_value="2",
        description="Rosmaster_Lib set_motor channel for the right rear motor.",
    )
    lock_front_steering_arg = DeclareLaunchArgument(
        "lock_front_steering",
        default_value="true",
        choices=["true", "false"],
        description="Hold the R2 front steering servos at the neutral relative angle.",
    )
    front_steering_lock_angle_arg = DeclareLaunchArgument(
        "front_steering_lock_angle",
        default_value="0.0",
        description="Relative steering angle used when locking the front servos.",
    )
    use_camera_arg = DeclareLaunchArgument(
        "use_camera",
        default_value="true",
        choices=["true", "false"],
        description="Start the ROSMASTER USB camera and publish ZED-compatible image topics.",
    )
    use_depth_camera_arg = DeclareLaunchArgument(
        "use_depth_camera",
        default_value="true",
        choices=["true", "false"],
        description="Start the ROSMASTER Orbbec depth camera and publish ZED-compatible point cloud topics.",
    )
    camera_video_device_arg = DeclareLaunchArgument(
        "camera_video_device",
        default_value="/dev/video0",
        description="V4L2 device for the ROSMASTER USB RGB camera.",
    )
    camera_width_arg = DeclareLaunchArgument(
        "camera_width",
        default_value="640",
        description="USB camera image width.",
    )
    camera_height_arg = DeclareLaunchArgument(
        "camera_height",
        default_value="480",
        description="USB camera image height.",
    )
    camera_fps_arg = DeclareLaunchArgument(
        "camera_fps",
        default_value="30.0",
        description="USB camera frame rate.",
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
                "car_type": ParameterValue(LaunchConfiguration("car_type"), value_type=int),
                "drive_mode": LaunchConfiguration("drive_mode"),
                "xlinear_limit": ParameterValue(LaunchConfiguration("max_linear_x"), value_type=float),
                "ylinear_limit": ParameterValue(LaunchConfiguration("max_linear_y"), value_type=float),
                "angular_limit": ParameterValue(LaunchConfiguration("max_angular_z"), value_type=float),
                "command_timeout_sec": ParameterValue(LaunchConfiguration("command_timeout_sec"), value_type=float),
                "max_motor_pwm": ParameterValue(LaunchConfiguration("max_motor_pwm"), value_type=float),
                "left_motor_channel": ParameterValue(LaunchConfiguration("left_motor_channel"), value_type=int),
                "right_motor_channel": ParameterValue(LaunchConfiguration("right_motor_channel"), value_type=int),
                "lock_front_steering": ParameterValue(LaunchConfiguration("lock_front_steering"), value_type=bool),
                "front_steering_lock_angle": ParameterValue(
                    LaunchConfiguration("front_steering_lock_angle"), value_type=float
                ),
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
                "output_standard_odom_topic": "/odom",
                "output_odom_topic": "/aiformula_sensing/gyro_odometry_publisher/odom",
                "output_wheel_odom_topic": "/aiformula_sensing/wheel_odometry_publisher/odom",
                "output_velocity_body_topic": "/aiformula_sensing/vectornav/velocity_body",
                "odom_frame_id": "odom",
                "base_frame_id": "base_footprint",
                "input_imu_topic": LaunchConfiguration("input_imu_topic"),
                "output_vectornav_imu_topic": "/aiformula_sensing/vectornav/imu",
                "output_zed_imu_topic": "/aiformula_sensing/zed_node/imu",
                "imu_frame_id": "imu_link",
                "publish_rear_potentiometer_zero": True,
                "rear_potentiometer_topic": "/aiformula_sensing/rear_potentiometer/yaw",
                "rear_potentiometer_period_sec": 0.1,
            }
        ],
    )

    joy_node = Node(
        package="joy",
        executable="joy_node",
        name="joy_node",
        namespace="/aiformula_control",
        output="screen",
        parameters=[
            {
                "device_id": ParameterValue(LaunchConfiguration("joy_device_id"), value_type=int),
                "deadzone": ParameterValue(LaunchConfiguration("joy_deadzone"), value_type=float),
                "autorepeat_rate": 20.0,
                "sticky_buttons": False,
                "coalesce_interval_ms": 1,
            }
        ],
        remappings=[
            ("joy", "joy_node/joy"),
        ],
        condition=IfCondition(LaunchConfiguration("use_joy")),
    )

    joy_mapper_node = Node(
        package="rosmaster_aiformula_bridge",
        executable="joy_diff_drive_mapper",
        name="joy_diff_drive_mapper",
        namespace="/aiformula_control",
        output="screen",
        parameters=[
            {
                "cmd_vel_topic": "/aiformula_control/game_pad/cmd_vel",
                "linear_axis": ParameterValue(LaunchConfiguration("joy_linear_axis"), value_type=int),
                "angular_axis": ParameterValue(LaunchConfiguration("joy_angular_axis"), value_type=int),
                "enable_button": ParameterValue(LaunchConfiguration("joy_enable_button"), value_type=int),
                "enable_axis": ParameterValue(LaunchConfiguration("joy_enable_axis"), value_type=int),
                "deadzone": ParameterValue(LaunchConfiguration("joy_deadzone"), value_type=float),
                "max_linear_x": ParameterValue(LaunchConfiguration("joy_max_linear_x"), value_type=float),
                "max_angular_z": ParameterValue(LaunchConfiguration("joy_max_angular_z"), value_type=float),
            }
        ],
        remappings=[
            ("joy", "joy_node/joy"),
        ],
        condition=IfCondition(LaunchConfiguration("use_joy")),
    )

    usb_camera_node = Node(
        package="usb_cam",
        executable="usb_cam_node_exe",
        name="camera",
        namespace="/usb_cam",
        output="screen",
        parameters=[
            {
                "video_device": LaunchConfiguration("camera_video_device"),
                "image_width": ParameterValue(LaunchConfiguration("camera_width"), value_type=int),
                "image_height": ParameterValue(LaunchConfiguration("camera_height"), value_type=int),
                "framerate": ParameterValue(LaunchConfiguration("camera_fps"), value_type=float),
                "pixel_format": "mjpeg2rgb",
                "camera_name": "rosmaster_usb_camera",
                "camera_info_url": f"file://{bringup_share / 'config' / 'rosmaster_usb_camera.yaml'}",
                "frame_id": "zed_left_camera_optical_frame",
            }
        ],
        condition=IfCondition(LaunchConfiguration("use_camera")),
    )

    astra_camera_node = Node(
        package="astra_camera",
        executable="astra_camera_node",
        name="camera",
        namespace="/camera",
        output="screen",
        parameters=[
            {
                "camera_name": "camera",
                "depth_registration": False,
                "enable_color": False,
                "enable_depth": True,
                "enable_point_cloud": True,
                "enable_colored_point_cloud": False,
                "enable_ir": False,
                "color_width": 640,
                "color_height": 480,
                "color_fps": 30,
                "depth_width": 640,
                "depth_height": 480,
                "depth_fps": 30,
                "publish_tf": True,
                "tf_publish_rate": 10.0,
                "connection_delay": 100,
                "oni_log_to_console": False,
                "oni_log_to_file": False,
            }
        ],
        condition=IfCondition(LaunchConfiguration("use_depth_camera")),
    )

    camera_compat_bridge_node = Node(
        package="rosmaster_aiformula_bridge",
        executable="camera_compat_bridge",
        name="rosmaster_camera_compat_bridge",
        output="screen",
        parameters=[
            {
                "input_color_image_topic": "/usb_cam/image_raw",
                "input_color_camera_info_topic": "/usb_cam/camera_info",
                "input_depth_image_topic": "/camera/depth/image_raw",
                "input_depth_camera_info_topic": "/camera/depth/camera_info",
                "input_point_cloud_topic": "/camera/depth/points",
                "output_left_image_topic": "/aiformula_sensing/zed_node/left_image/undistorted",
                "output_right_image_topic": "/aiformula_sensing/zed_node/right_image/undistorted",
                "output_left_camera_info_topic": "/aiformula_sensing/zed_node/left/camera_info",
                "output_right_camera_info_topic": "/aiformula_sensing/zed_node/right/camera_info",
                "output_depth_image_topic": "/aiformula_sensing/zed_node/depth/depth_registered",
                "output_depth_camera_info_topic": "/aiformula_sensing/zed_node/depth/camera_info",
                "output_point_cloud_topic": "/aiformula_sensing/zed_node/point_cloud/cloud_registered",
                "publish_depth": ParameterValue(LaunchConfiguration("use_depth_camera"), value_type=bool),
                "publish_point_cloud": ParameterValue(LaunchConfiguration("use_depth_camera"), value_type=bool),
            }
        ],
        condition=IfCondition(LaunchConfiguration("use_camera")),
    )

    return LaunchDescription(
        [
            model_arg,
            car_type_arg,
            drive_mode_arg,
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
            command_timeout_arg,
            use_joy_arg,
            joy_device_id_arg,
            joy_deadzone_arg,
            joy_enable_button_arg,
            joy_enable_axis_arg,
            joy_linear_axis_arg,
            joy_angular_axis_arg,
            joy_max_linear_x_arg,
            joy_max_angular_z_arg,
            max_motor_pwm_arg,
            left_motor_channel_arg,
            right_motor_channel_arg,
            lock_front_steering_arg,
            front_steering_lock_angle_arg,
            use_camera_arg,
            use_depth_camera_arg,
            camera_video_device_arg,
            camera_width_arg,
            camera_height_arg,
            camera_fps_arg,
            robot_state_publisher_node,
            driver_node,
            base_node,
            imu_filter_node,
            compat_bridge_node,
            usb_camera_node,
            astra_camera_node,
            camera_compat_bridge_node,
            joy_node,
            joy_mapper_node,
        ]
    )
