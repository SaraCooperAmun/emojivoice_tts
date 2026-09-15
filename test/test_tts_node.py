import unittest

from unittest import mock

from emojivoice_tts.tts_node import EMOJI_MAPPING, TtsNode


class TestParseEmotionTag(unittest.TestCase):

    def setUp(self):
        self.node = TtsNode.__new__(TtsNode)
        self.node._logger = mock.MagicMock()

    def test_all_emoji_mappings(self):
        for emoji, expected_id in EMOJI_MAPPING.items():
            text = (
                f'<voice_expression({emoji})>'
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
            '<voice_expression(happy)>'
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
