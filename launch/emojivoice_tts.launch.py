import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_dir = get_package_share_directory('emojivoice_tts')
    config_file = os.path.join(package_dir, 'config', 'emojivoice.yaml')

    viseme_mode = LaunchConfiguration('viseme_mode')

    return LaunchDescription([
        DeclareLaunchArgument(
            'viseme_mode',
            default_value='normal',
            description='Viseme mode: normal, static, or open_close',
        ),

        Node(
            package='emojivoice_tts',
            executable='tts_node',
            name='tts_node',
            output='screen',
            parameters=[
                config_file,
                {
                    'viseme_mode': viseme_mode,
                },
            ],
        ),
    ])