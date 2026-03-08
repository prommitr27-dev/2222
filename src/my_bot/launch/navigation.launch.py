import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    package_name = 'my_bot'
    pkg_dir = get_package_share_directory(package_name)
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    map_file = '/home/p/my_robot_ws/22.yaml'
    params_file = os.path.join(pkg_dir, 'config', 'nav2_params.yaml')

    log_dir = '/home/p/my_robot_ws/nav2_logs'
    os.makedirs(log_dir, exist_ok=True)

    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'map': map_file,
            'use_sim_time': 'true',
            'params_file': params_file,
            'autostart': 'true',
            'log_level': 'info',
        }.items()
    )

    delayed_nav2 = TimerAction(
        period=5.0,
        actions=[nav2_bringup]
    )

    cmd_vel_logger = ExecuteProcess(
        cmd=[
            'bash', '-c',
            f'ros2 topic echo /cmd_vel 2>&1 | '
            f'while IFS= read -r line; do '
            f'echo "$(date +%T.%3N) $line"; '
            f'done >> {log_dir}/cmd_vel.log'
        ],
        output='log'
    )

    bt_logger = ExecuteProcess(
        cmd=[
            'bash', '-c',
            f'ros2 topic echo /behavior_tree_log 2>&1 | '
            f'while IFS= read -r line; do '
            f'echo "$(date +%T.%3N) $line"; '
            f'done >> {log_dir}/bt.log'
        ],
        output='log'
    )

    amcl_logger = ExecuteProcess(
        cmd=[
            'bash', '-c',
            f'ros2 topic echo /amcl_pose 2>&1 | '
            f'while IFS= read -r line; do '
            f'echo "$(date +%T.%3N) $line"; '
            f'done >> {log_dir}/amcl_pose.log'
        ],
        output='log'
    )

    nav_status_logger = ExecuteProcess(
        cmd=[
            'bash', '-c',
            f'ros2 topic echo /navigate_to_pose/_action/status 2>&1 | '
            f'while IFS= read -r line; do '
            f'echo "$(date +%T.%3N) $line"; '
            f'done >> {log_dir}/nav_status.log'
        ],
        output='log'
    )

    delayed_loggers = TimerAction(
        period=10.0,
        actions=[
            cmd_vel_logger,
            bt_logger,
            amcl_logger,
            nav_status_logger,
        ]
    )

    return LaunchDescription([
        delayed_nav2,
        delayed_loggers,
    ])
