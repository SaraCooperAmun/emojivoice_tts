#!/usr/bin/env python3

import base64
import json
import os
import re
import subprocess
import threading
import time

from communication_skills.action import Say

import numpy as np

import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.action.server import ServerGoalHandle
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

import sounddevice as sd

from std_msgs.msg import Bool, String

WORKER_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'emojivoice_worker.py',
)


# ==============================================================
# EmojiVoice emotion mapping
# ==============================================================

EMOJI_MAPPING = {
    '😍': 107,
    '😡': 58,
    '😎': 79,
    '😭': 103,
    '🙄': 66,
    '😁': 18,
    '🙂': 12,
    '🤣': 15,
    '😮': 54,
    '😅': 22,
    '🤔': 17,
}


class TtsNode(Node):

    def __init__(self):
        super().__init__('tts_node')

        # ----------------------------------------------------------
        # Parameters
        # ----------------------------------------------------------
        self.declare_parameter(
            'emojivoice_python',
            ''
        )

        self.declare_parameter(
            'tts_model_path',
            ''
        )
        self.declare_parameter('frame_id', '')
        self.declare_parameter('language', 'en')

        self.frame_id = (
            self.get_parameter('frame_id')
            .get_parameter_value()
            .string_value
        )

        self._language = (
            self.get_parameter('language')
            .get_parameter_value()
            .string_value
        )

        # EmojiVoice currently uses English.
        if self._language != 'en':
            self.get_logger().warning(
                f"EmojiVoice uses English, but language='{self._language}'"
            )
        self.emojivoice_python = (
            self.get_parameter('emojivoice_python')
            .get_parameter_value()
            .string_value
        )

        self.tts_model_path = (
            self.get_parameter('tts_model_path')
            .get_parameter_value()
            .string_value
        )
        if not self.emojivoice_python:
            raise RuntimeError(
                'Parameter "emojivoice_python" is required.'
            )

        if not self.tts_model_path:
            raise RuntimeError(
                'Parameter "tts_model_path" is required.'
            )
        # ----------------------------------------------------------
        # Robot speaking state
        # ----------------------------------------------------------

        self.robot_speaks = False

        self.voice_detected_sub = self.create_subscription(
            Bool,
            '/robot_speaking',
            self.on_robot_speaking,
            1,
        )

        # ----------------------------------------------------------
        # Speech metadata
        # ----------------------------------------------------------

        self.speech_publisher = self.create_publisher(
            String,
            '/tts/speech',
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
            'Starting EmojiVoice worker...'
        )

        self.worker = subprocess.Popen(
            [
                self.emojivoice_python,
                WORKER_PATH,
                '--model-path',
                self.tts_model_path,
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
        # /tts/say action server
        # ----------------------------------------------------------

        self._action_server = ActionServer(
            self,
            Say,
            '/tts/say',
            execute_callback=self.execute_callback,
            goal_callback=self.goal_callback,
            handle_accepted_callback=self.handle_accepted_callback,
            cancel_callback=self.cancel_callback,
            callback_group=ReentrantCallbackGroup(),
        )

        self.get_logger().info(
            '=============================================='
        )

        self.get_logger().info(
            'EmojiVoice TTS ROS node started'
        )

        self.get_logger().info(
            '  Say action:      /tts/say'
        )

        self.get_logger().info(
            '  Speech metadata: /tts/speech'
        )

        self.get_logger().info(
            '  Robot speaking:  /robot_speaking'
        )

        self.get_logger().info(
            '=============================================='
        )

    # ==============================================================
    # Worker startup
    # ==============================================================

    def _wait_for_worker(self):

        self.get_logger().info(
            'Waiting for EmojiVoice models to load...'
        )

        while True:

            line = self.worker.stdout.readline()

            if not line:

                if self.worker.poll() is not None:
                    raise RuntimeError(
                        'EmojiVoice worker exited while loading models.'
                    )

                continue

            line = line.rstrip()

            self.get_logger().info(
                f'[EmojiVoice] {line}'
            )

            if line == 'EmojiVoice models loaded.':

                self.worker_ready = True

                self.get_logger().info(
                    'EmojiVoice worker is ready.'
                )

                return

    # ==============================================================
    # Voice expression parsing
    # ==============================================================

    def parse_emotion_tag(self, text):
        """
        Extract voice expression from the Dialogue Manager format.

        Supported:

            <voice_expression(😍)>Hello!</voice_expression>

        Returns
        -------
        tuple
            clean_text, emotion, where emotion is the EmojiVoice emotion ID.

        """
        if not text:
            return text, 'neutral'

        pattern = re.compile(
            r'^\s*'
            r'<voice_expression\(\s*(.*?)\s*\)>'
            r'(.*?)'
            r'</voice_expression>'
            r'\s*$',
            re.IGNORECASE | re.DOTALL,
        )

        match = pattern.match(text)

        if match:

            expression = match.group(1).strip()
            clean_text = match.group(2).strip()

            if expression not in EMOJI_MAPPING:

                self.get_logger().warning(
                    f'Unknown voice expression emoji: '
                    f"'{expression}'. Using neutral."
                )

                return clean_text, 'neutral'

            emotion = str(EMOJI_MAPPING[expression])

            self.get_logger().info(
                f'Voice expression detected: '
                f"'{expression}' -> EmojiVoice emotion {emotion}"
            )

            self.get_logger().info(
                f"Clean speech text: '{clean_text}'"
            )

            return clean_text, emotion

        # No voice expression tag -> neutral.
        return text.strip(), 'neutral'

    # ==============================================================
    # Send request to EmojiVoice
    # ==============================================================

    def generate_speech(self, text, emotion):

        if not self.worker_ready:
            raise RuntimeError(
                'EmojiVoice worker is not ready.'
            )

        request = {
            'text': text,
            'emotion': emotion,
        }

        with self.worker_lock:

            self.worker.stdin.write(
                json.dumps(
                    request,
                    ensure_ascii=False,
                )
                + '\n'
            )

            self.worker.stdin.flush()

            line = self.worker.stdout.readline()

        if not line:
            raise RuntimeError(
                'EmojiVoice worker stopped unexpectedly.'
            )

        response = json.loads(line)

        if not response.get('ok', False):
            raise RuntimeError(
                response.get(
                    'error',
                    'Unknown EmojiVoice error',
                )
            )

        audio_bytes = base64.b64decode(
            response['audio']
        )

        audio_array = np.frombuffer(
            audio_bytes,
            dtype=np.float32,
        ).copy()

        sample_rate = int(
            response['sample_rate']
        )

        duration = float(
            response['duration']
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
    #
    # Publishes word-level Say feedback during playback.
    # ==============================================================

    def play_audio(
        self,
        audio_array,
        sample_rate,
        goal_handle=None,
        words=None,
    ):

        if audio_array is None:
            return False

        try:

            self.get_logger().info(
                f'Playing audio: '
                f'{len(audio_array)} samples @ {sample_rate} Hz'
            )

            # ------------------------------------------------------
            # Start playback using sounddevice.
            # ------------------------------------------------------

            playback_start = time.monotonic()

            sd.play(
                audio_array,
                sample_rate,
            )

            # ------------------------------------------------------
            # Playback information
            # ------------------------------------------------------

            total_samples = len(audio_array)

            if sample_rate > 0:
                total_duration = (
                    total_samples / sample_rate
                )
            else:
                total_duration = 0.0

            last_word_index = -1

            # ------------------------------------------------------
            # Wait while keeping ROS action cancellation responsive.
            # ------------------------------------------------------

            while sd.get_stream() is not None:

                # --------------------------------------------------
                # Cancellation
                # --------------------------------------------------

                if (
                    goal_handle is not None
                    and goal_handle.is_cancel_requested
                ):

                    self.get_logger().warning(
                        'Say cancellation requested during playback.'
                    )

                    sd.stop()

                    return False

                stream = sd.get_stream()

                if stream is None:
                    break

                if not stream.active:
                    break

                # --------------------------------------------------
                # Word-level feedback
                #
                # The generated audio does not provide exact word
                # timestamps, so feedback is distributed according
                # to playback progress.
                # --------------------------------------------------

                if words and total_duration > 0:

                    elapsed = (
                        time.monotonic()
                        - playback_start
                    )

                    progress = min(
                        max(
                            elapsed / total_duration,
                            0.0,
                        ),
                        1.0,
                    )

                    word_index = min(
                        int(
                            progress * len(words)
                        ),
                        len(words) - 1,
                    )

                    if word_index != last_word_index:

                        feedback = Say.Feedback()

                        feedback.feedback.data_str = (
                            words[word_index]
                        )

                        goal_handle.publish_feedback(
                            feedback
                        )

                        self.get_logger().info(
                            '[SAY FEEDBACK] '
                            f"word='{words[word_index]}'"
                        )

                        last_word_index = word_index

                time.sleep(0.05)

            # ------------------------------------------------------
            # Ensure playback has completely finished.
            # ------------------------------------------------------

            sd.wait()

            return True

        except Exception as exc:

            self.get_logger().error(
                f'Audio playback failed: {exc}'
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
            'text': text,
            'duration': float(duration),
        }

        msg = String()

        msg.data = json.dumps(
            payload,
            ensure_ascii=False,
        )

        self.speech_publisher.publish(msg)

        self.get_logger().info(
            'Published /tts/speech: '
            f"text='{text}', "
            f'duration={duration:.3f}s'
        )

    # ==============================================================
    # Action callbacks
    # ==============================================================

    def goal_callback(
        self,
        goal_request,
    ):

        raw_input = goal_request.input.strip()

        self.get_logger().info(
            f"Received /tts/say: '{raw_input}'"
        )

        if not raw_input:

            self.get_logger().warning(
                'Rejecting empty Say goal.'
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
            'Say cancellation requested.'
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
        # Parse voice expression
        # ----------------------------------------------------------

        raw_input = request.input.strip()

        text, emotion = self.parse_emotion_tag(
            raw_input
        )

        if not text:

            result.result.error_msg = (
                'Say input is empty after removing '
                'voice expression tag.'
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
        # Synthesis + playback
        # ----------------------------------------------------------

        with self.audio_lock:

            # ------------------------------------------------------
            # Check cancellation before synthesis.
            # ------------------------------------------------------

            if goal_handle.is_cancel_requested:

                result.result.error_msg = (
                    'Say action cancelled.'
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
                    f'EmojiVoice generation failed: {exc}'
                )

                result.result.error_msg = (
                    f'TTS generation failed: {exc}'
                )

                goal_handle.abort()

                return result

            # ------------------------------------------------------
            # Check cancellation before playback.
            # ------------------------------------------------------

            if goal_handle.is_cancel_requested:

                result.result.error_msg = (
                    'Say action cancelled.'
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
                'Starting audio playback...'
            )

            # Only in the case of the robot!!
            time.sleep(2.0)

            # ------------------------------------------------------
            # Prepare word-level feedback.
            # ------------------------------------------------------

            words = text.split()

            playback_ok = self.play_audio(
                audio_array,
                sample_rate,
                goal_handle,
                words,
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
                    'Say action cancelled during playback.'
                )

                if goal_handle.is_cancel_requested:

                    goal_handle.canceled()

                else:

                    goal_handle.abort()

                return result

            self.get_logger().info(
                'Audio playback finished.'
            )

        # ----------------------------------------------------------
        # Finished
        # ----------------------------------------------------------

        result.result.error_msg = ''

        goal_handle.succeed()

        self.get_logger().info(
            'Say action completed successfully.'
        )

        return result

    # ==============================================================
    # Robot speaking
    # ==============================================================

    def on_robot_speaking(
        self,
        msg,
    ):

        self.robot_speaks = msg.data

    # ==============================================================
    # Cleanup
    # ==============================================================

    def destroy_node(self):

        self.get_logger().info(
            'Stopping EmojiVoice worker...'
        )

        if hasattr(self, 'worker'):

            try:

                self.worker.terminate()

                self.worker.wait(
                    timeout=3
                )

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


if __name__ == '__main__':
    main()
