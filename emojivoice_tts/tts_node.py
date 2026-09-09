#!/usr/bin/env python3

import base64
import json
import os
import re
import threading
import time
import subprocess
import numpy as np
import sounddevice as sd

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.action.server import ServerGoalHandle
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from std_msgs.msg import Bool, String

from communication_skills.action import Say


# ==============================================================
# EmojiVoice Python environment
# ==============================================================

# EMOJIVOICE_PYTHON = (
#     "/home/emorobcare/.local/share/mamba/envs/emojivoice/bin/python"
# )

EMOJIVOICE_PYTHON = (
    "/home/nvidia/sara_vizij/do_you_feel_me/emojivoice_env/bin/python"
)

WORKER_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "emojivoice_worker.py",
)


class TtsNode(Node):

    def __init__(self):

        super().__init__("tts_node")

        # ----------------------------------------------------------
        # Parameters
        # ----------------------------------------------------------

        self.declare_parameter("frame_id", "")
        self.declare_parameter("language", "en")

        self.frame_id = (
            self.get_parameter("frame_id")
            .get_parameter_value()
            .string_value
        )

        self._language = (
            self.get_parameter("language")
            .get_parameter_value()
            .string_value
        )

        # EmojiVoice currently uses English.
        if self._language != "en":
            self.get_logger().warning(
                f"EmojiVoice uses English, but language='{self._language}'"
            )

        # ----------------------------------------------------------
        # Default emotion
        # ----------------------------------------------------------

        self._emotion = "neutral"

        # ----------------------------------------------------------
        # Robot speaking state
        # ----------------------------------------------------------

        self.robot_speaks = False

        self.voice_detected_sub = self.create_subscription(
            Bool,
            "/robot_speaking",
            self.on_robot_speaking,
            1,
        )

        # ----------------------------------------------------------
        # Speech metadata
        # ----------------------------------------------------------

        self.speech_publisher = self.create_publisher(
            String,
            "/tts/speech",
            10,
        )

        # ----------------------------------------------------------
        # Only one synthesis/playback operation at a time.
        # ----------------------------------------------------------

        self.audio_lock = threading.Lock()

        # ----------------------------------------------------------
        # Start EmojiVoice worker
        # ----------------------------------------------------------

        self.get_logger().info(
            "Starting EmojiVoice worker..."
        )

        self.worker = subprocess.Popen(
            [
                EMOJIVOICE_PYTHON,
                WORKER_PATH,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            bufsize=1,
        )

        # The worker prints its model-loading messages to stdout
        # before accepting requests.
        self.worker_ready = False

        self.worker_lock = threading.Lock()

        self._wait_for_worker()

        # ----------------------------------------------------------
        # /skill/say action server
        # ----------------------------------------------------------

        self._action_server = ActionServer(
            self,
            Say,
            "/skill/say",
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            handle_accepted_callback=self.handle_accepted_callback,
            cancel_callback=self.cancel_callback,
            callback_group=ReentrantCallbackGroup(),
        )

        self.get_logger().info(
            "=============================================="
        )
        self.get_logger().info(
            "EmojiVoice TTS ROS node started"
        )
        self.get_logger().info(
            "  Say action:      /skill/say"
        )
        self.get_logger().info(
            "  Speech metadata: /tts/speech"
        )
        self.get_logger().info(
            "  Robot speaking:  /robot_speaking"
        )
        self.get_logger().info(
            "=============================================="
        )

    # ==============================================================
    # Worker startup
    # ==============================================================

    def _wait_for_worker(self):

        self.get_logger().info(
            "Waiting for EmojiVoice models to load..."
        )

        while True:

            line = self.worker.stdout.readline()

            if not line:

                if self.worker.poll() is not None:

                    raise RuntimeError(
                        "EmojiVoice worker exited while loading models."
                    )

                continue

            line = line.rstrip()

            self.get_logger().info(
                f"[EmojiVoice] {line}"
            )

            if line == "EmojiVoice models loaded.":

                self.worker_ready = True

                self.get_logger().info(
                    "EmojiVoice worker is ready."
                )

                return

    # ==============================================================
    # Emotion parsing
    # ==============================================================

    def parse_emotion_tag(self, text):

        if not text:
            return text, self._emotion

        # <emotion happy>Hello</emotion>
        # <emotion=happy>Hello</emotion>
        # <emotion   happy>Hello</emotion>

        wrapped_pattern = re.compile(
            r"^\s*"
            r"<emotion"
            r"(?:\s*=\s*|\s+)"
            r"([A-Za-z0-9_.-]+)"
            r"\s*>"
            r"(.*?)"
            r"</emotion>"
            r"\s*$",
            re.IGNORECASE | re.DOTALL,
        )

        match = wrapped_pattern.match(text)

        if match:

            emotion = match.group(1).strip().lower()
            clean_text = match.group(2).strip()

            return clean_text, emotion

        # <emotion(happy)>Hello

        parenthesized_pattern = re.compile(
            r"^\s*"
            r"<emotion\s*\(\s*"
            r"([A-Za-z0-9_.-]+)"
            r"\s*\)\s*>"
            r"(.*)$",
            re.IGNORECASE | re.DOTALL,
        )

        match = parenthesized_pattern.match(text)

        if match:

            emotion = match.group(1).strip().lower()
            clean_text = match.group(2).strip()

            return clean_text, emotion

        return text.strip(), self._emotion

    # ==============================================================
    # Send request to EmojiVoice
    # ==============================================================

    def generate_speech(self, text, emotion):

        if not self.worker_ready:

            raise RuntimeError(
                "EmojiVoice worker is not ready."
            )

        request = {
            "text": text,
            "emotion": emotion,
        }

        with self.worker_lock:

            self.worker.stdin.write(
                json.dumps(
                    request,
                    ensure_ascii=False,
                )
                + "\n"
            )

            self.worker.stdin.flush()

            line = self.worker.stdout.readline()

        if not line:

            raise RuntimeError(
                "EmojiVoice worker stopped unexpectedly."
            )

        response = json.loads(line)

        if not response.get("ok", False):

            raise RuntimeError(
                response.get(
                    "error",
                    "Unknown EmojiVoice error",
                )
            )

        audio_bytes = base64.b64decode(
            response["audio"]
        )

        audio_array = np.frombuffer(
            audio_bytes,
            dtype=np.float32,
        ).copy()

        sample_rate = int(
            response["sample_rate"]
        )

        duration = float(
            response["duration"]
        )

        return (
            audio_array,
            sample_rate,
            duration,
        )

    # ==============================================================
    # Playback
    #
    # Uses sounddevice, exactly like the standalone
    # tts_synthesise.py script.
    # ==============================================================

    def play_audio(
        self,
        audio_array,
        sample_rate,
        goal_handle=None,
    ):

        if audio_array is None:
            return False

        try:

            self.get_logger().info(
                f"Playing audio: "
                f"{len(audio_array)} samples @ {sample_rate} Hz"
            )

            # ------------------------------------------------------
            # Start playback using sounddevice.
            #
            # This is the same backend used by:
            #
            #     sd.play(audio, 22050)
            #     sd.wait()
            #
            # in tts_synthesise.py
            # ------------------------------------------------------

            sd.play(
                audio_array,
                sample_rate,
            )

            # ------------------------------------------------------
            # Wait while keeping ROS action cancellation responsive.
            # ------------------------------------------------------

            while sd.get_stream() is not None:

                if (
                    goal_handle is not None
                    and goal_handle.is_cancel_requested
                ):

                    self.get_logger().warning(
                        "Say cancellation requested during playback."
                    )

                    sd.stop()

                    return False

                time.sleep(0.05)

                # sounddevice's global playback stream becomes
                # inactive once playback has finished.
                stream = sd.get_stream()

                if stream is None:
                    break

                if not stream.active:
                    break

            # ------------------------------------------------------
            # Ensure playback has completely finished.
            # ------------------------------------------------------

            sd.wait()

            return True

        except Exception as exc:

            self.get_logger().error(
                f"Audio playback failed: {exc}"
            )

            return False

        finally:

            try:
                sd.stop()
            except Exception:
                pass

    # ==============================================================
    # /tts/speech
    # ==============================================================

    def publish_speech_metadata(
        self,
        text,
        duration,
    ):

        payload = {
            "text": text,
            "duration": float(duration),
        }

        msg = String()

        msg.data = json.dumps(
            payload,
            ensure_ascii=False,
        )

        self.speech_publisher.publish(msg)

        self.get_logger().info(
            "Published /tts/speech: "
            f"text='{text}', "
            f"duration={duration:.3f}s"
        )

    # ==============================================================
    # Action callbacks
    # ==============================================================

    def goal_callback(self, goal_request):

        raw_input = goal_request.input.strip()

        self.get_logger().info(
            f"Received /skill/say: '{raw_input}'"
        )

        if not raw_input:

            self.get_logger().warning(
                "Rejecting empty Say goal."
            )

            return GoalResponse.REJECT

        return GoalResponse.ACCEPT

    # --------------------------------------------------------------

    def handle_accepted_callback(
        self,
        goal_handle: ServerGoalHandle,
    ):

        goal_handle.execute()

    # --------------------------------------------------------------

    def cancel_callback(
        self,
        goal_handle: ServerGoalHandle,
    ):

        self.get_logger().info(
            "Say cancellation requested."
        )

        return CancelResponse.ACCEPT

    # ==============================================================
    # Say execution
    # ==============================================================

    def execute_callback(
        self,
        goal_handle: ServerGoalHandle,
    ):

        request = goal_handle.request

        result = Say.Result()

        # ----------------------------------------------------------
        # Parse emotion
        # ----------------------------------------------------------

        raw_input = request.input.strip()

        text, emotion = self.parse_emotion_tag(
            raw_input
        )

        if not text:

            result.result.error_msg = (
                "Say input is empty after removing emotion tag."
            )

            goal_handle.abort()

            return result

        self.get_logger().info(
            f"Speech text: '{text}'"
        )

        self.get_logger().info(
            f"Speech emotion: '{emotion}'"
        )

        # ----------------------------------------------------------
        # Feedback: generation starting
        # ----------------------------------------------------------

        feedback = Say.Feedback()

        goal_handle.publish_feedback(
            feedback
        )

        # ----------------------------------------------------------
        # Synthesis + playback
        # ----------------------------------------------------------

        with self.audio_lock:

            if goal_handle.is_cancel_requested:

                result.result.error_msg = (
                    "Say action cancelled."
                )

                goal_handle.canceled()

                return result

            # ------------------------------------------------------
            # Generate
            # ------------------------------------------------------

            try:

                (
                    audio_array,
                    sample_rate,
                    duration,
                ) = self.generate_speech(
                    text,
                    emotion,
                )

            except Exception as exc:

                self.get_logger().error(
                    f"EmojiVoice generation failed: {exc}"
                )

                result.result.error_msg = (
                    f"TTS generation failed: {exc}"
                )

                goal_handle.abort()

                return result

            # ------------------------------------------------------
            # Check cancellation before playback
            # ------------------------------------------------------

            if goal_handle.is_cancel_requested:

                result.result.error_msg = (
                    "Say action cancelled."
                )

                goal_handle.canceled()

                return result

            # ------------------------------------------------------
            # Tell Vizij about the speech BEFORE audio starts.
            #
            # This keeps the viseme timing synchronized.
            # ------------------------------------------------------

            self.publish_speech_metadata(
                text,
                duration,
            )

            # ------------------------------------------------------
            # Playback
            # ------------------------------------------------------

            self.robot_speaks = True

            self.get_logger().info(
                "Starting audio playback..."
            )
            #Only in the case of the robot!!
            time.sleep(2.0)
            playback_ok = self.play_audio(
                audio_array,
                sample_rate,
                goal_handle,
            )

            self.robot_speaks = False

            # ------------------------------------------------------
            # Playback failed/cancelled
            # ------------------------------------------------------

            if (
                not playback_ok
                or goal_handle.is_cancel_requested
            ):

                result.result.error_msg = (
                    "Say action cancelled during playback."
                )

                if goal_handle.is_cancel_requested:

                    goal_handle.canceled()

                else:

                    goal_handle.abort()

                return result

            self.get_logger().info(
                "Audio playback finished."
            )

        # ----------------------------------------------------------
        # Finished
        # ----------------------------------------------------------

        feedback = Say.Feedback()

        goal_handle.publish_feedback(
            feedback
        )

        result.result.error_msg = ""

        goal_handle.succeed()

        self.get_logger().info(
            "Say action completed successfully."
        )

        return result

    # ==============================================================
    # Robot speaking
    # ==============================================================

    def on_robot_speaking(self, msg):

        self.robot_speaks = msg.data

    # ==============================================================
    # Cleanup
    # ==============================================================

    def destroy_node(self):

        self.get_logger().info(
            "Stopping EmojiVoice worker..."
        )

        if hasattr(self, "worker"):

            try:

                self.worker.terminate()
                self.worker.wait(timeout=3)

            except Exception:

                try:
                    self.worker.kill()
                except Exception:
                    pass

        # Make sure any sounddevice playback is stopped.
        try:
            sd.stop()
        except Exception:
            pass

        super().destroy_node()


# ==============================================================
# MAIN
# ==============================================================

def main():

    rclpy.init()

    node = TtsNode()

    executor = MultiThreadedExecutor()

    executor.add_node(node)

    try:

        executor.spin()

    except KeyboardInterrupt:
        pass

    finally:

        executor.shutdown()

        node.destroy_node()

        rclpy.shutdown()


if __name__ == "__main__":
    main()
