import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    package_dir = get_package_share_directory('emojivoice_tts')
    config_file = os.path.join(package_dir, 'config', 'emojivoice.yaml')

    return LaunchDescription([
        Node(
            package='emojivoice_tts',
            executable='tts_node',
            name='tts_node',
            output='screen',
            parameters=[config_file],
        ),
    ])
