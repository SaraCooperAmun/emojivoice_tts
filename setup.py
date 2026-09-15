from setuptools import find_packages, setup
import os 
from glob import glob

package_name = "emojivoice_tts"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    package_data={
        package_name: [
            "emojivoice_worker.py",
        ],
    },
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            ["resource/" + package_name],
        ),
        (
            "share/" + package_name,
            ["package.xml"],
        ),
        (
            os.path.join("share", "emojivoice_tts", "launch"),
            glob("launch/*.launch.py"),
        ),
        (
            os.path.join("share", "emojivoice_tts", "config"),
            glob("config/*.yaml"),
        ),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="emorobcare",
    maintainer_email="emorobcare@todo.todo",
    description="ROS 2 TTS server using EmojiVoice / Matcha-TTS.",
    license="MIT-0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "tts_node = emojivoice_tts.tts_node:main",
        ],
    },
)