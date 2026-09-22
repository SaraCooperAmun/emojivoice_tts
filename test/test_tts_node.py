import unittest

from unittest import mock

from emojivoice_tts.tts_node import (
    TtsNode,
    VOICE_EXPRESSION_MAPPING,
)


class TestParseEmotionTag(unittest.TestCase):

    def setUp(self):
        self.node = TtsNode.__new__(TtsNode)
        self.node._logger = mock.MagicMock()

    def test_all_voice_expression_mappings(self):
        for expression, expected_id in VOICE_EXPRESSION_MAPPING.items():
            text = (
                f'<voice_expression({expression})>'
                'Hello!'
                '</voice_expression>'
            )

            clean_text, emotion = (
                self.node.parse_emotion_tag(text)
            )

            self.assertEqual(clean_text, 'Hello!')
            self.assertEqual(emotion, str(expected_id))

    def test_love_emoji_maps_to_107(self):
        text = (
            '<voice_expression(😍)>'
            'Hello!'
            '</voice_expression>'
        )

        clean_text, emotion = (
            self.node.parse_emotion_tag(text)
        )

        self.assertEqual(clean_text, 'Hello!')
        self.assertEqual(emotion, '107')

    def test_happy_string_maps_to_18(self):
        text = (
            '<voice_expression(happy)>'
            'Hello!'
            '</voice_expression>'
        )

        clean_text, emotion = (
            self.node.parse_emotion_tag(text)
        )

        self.assertEqual(clean_text, 'Hello!')
        self.assertEqual(emotion, '18')

    def test_sad_string_maps_to_103(self):
        text = (
            '<voice_expression(sad)>'
            'Hello!'
            '</voice_expression>'
        )

        clean_text, emotion = (
            self.node.parse_emotion_tag(text)
        )

        self.assertEqual(clean_text, 'Hello!')
        self.assertEqual(emotion, '103')

    def test_publish_viseme_publishes_single_viseme(self):
        self.node.viseme_publisher = mock.MagicMock()

        self.node.publish_viseme(12)

        self.node.viseme_publisher.publish.assert_called_once()

        msg = self.node.viseme_publisher.publish.call_args[0][0]

        self.assertEqual(len(msg.visemes), 1)
        self.assertEqual(msg.visemes[0].value, 12)
        self.assertEqual(msg.visemes[0].time, 0.0)
        self.assertEqual(msg.visemes[0].duration, 0.0)

    def test_publish_viseme_publishes_each_viseme_individually(self):
        self.node.viseme_publisher = mock.MagicMock()

        for value in [12, 8, 13, 14, 0]:
            self.node.publish_viseme(value)

        self.assertEqual(
            self.node.viseme_publisher.publish.call_count,
            5,
        )

        published_values = [
            call.args[0].visemes[0].value
            for call in self.node.viseme_publisher.publish.call_args_list
        ]

        self.assertEqual(
            published_values,
            [12, 8, 13, 14, 0],
        )

    def test_no_expression_uses_neutral(self):
        clean_text, emotion = (
            self.node.parse_emotion_tag('Hello world!')
        )

        self.assertEqual(clean_text, 'Hello world!')
        self.assertEqual(emotion, 'neutral')

    def test_empty_text_uses_neutral(self):
        clean_text, emotion = (
            self.node.parse_emotion_tag('')
        )

        self.assertEqual(clean_text, '')
        self.assertEqual(emotion, 'neutral')

    def test_unknown_expression_uses_neutral(self):
        text = (
            '<voice_expression(not_an_emotion)>'
            'Hello!'
            '</voice_expression>'
        )

        clean_text, emotion = (
            self.node.parse_emotion_tag(text)
        )

        self.assertEqual(clean_text, 'Hello!')
        self.assertEqual(emotion, 'neutral')

    def test_expression_with_whitespace(self):
        text = (
            '  <voice_expression(  😍  )>'
            '  Hello!  '
            '</voice_expression>  '
        )

        clean_text, emotion = (
            self.node.parse_emotion_tag(text)
        )

        self.assertEqual(clean_text, 'Hello!')
        self.assertEqual(emotion, '107')

    def test_multiline_expression(self):
        text = (
            '<voice_expression(😍)>'
            'Hello\n'
            'this is a test!'
            '</voice_expression>'
        )

        clean_text, emotion = (
            self.node.parse_emotion_tag(text)
        )

        self.assertEqual(
            clean_text,
            'Hello\nthis is a test!',
        )
        self.assertEqual(emotion, '107')

    def test_malformed_expression_is_neutral(self):
        text = '<voice_expression(😍)>Hello!'

        clean_text, emotion = (
            self.node.parse_emotion_tag(text)
        )

        self.assertEqual(clean_text, text.strip())
        self.assertEqual(emotion, 'neutral')


if __name__ == '__main__':
    unittest.main()
