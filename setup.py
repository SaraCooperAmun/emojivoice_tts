from setuptools import find_packages, setup

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