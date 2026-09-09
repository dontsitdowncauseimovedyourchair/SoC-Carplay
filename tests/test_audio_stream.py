import unittest

from carplay_project.audio_stream import audio_event, end_event, iter_audio


class AudioStreamTests(unittest.TestCase):
    def test_fragmented_and_coalesced_network_chunks(self):
        data = audio_event(b'\0\0' * 100) + audio_event(b'\1\0' * 100) + end_event()
        for size in (1, 3, 1024, len(data)):
            with self.subTest(size=size):
                chunks = (data[i:i + size] for i in range(0, len(data), size))
                self.assertEqual(b''.join(iter_audio(chunks, 1000)), b'\0\0' * 100 + b'\1\0' * 100)

    def test_rejects_missing_completion_invalid_frames_and_extra_audio(self):
        cases = [b'', audio_event(b'\0\0'), b'{}\n', b'[]\n', b'x' * 8193,
                 audio_event(b'x') + end_event(), end_event(),
                 audio_event(b'\0\0') + end_event() + audio_event(b'\0\0'),
                 audio_event(b'\0\0') + end_event()[:-1]]
        for data in cases:
            with self.subTest(data=data[:50]), self.assertRaises(ValueError):
                list(iter_audio([data], 10000))

    def test_error_event_and_size_limit(self):
        with self.assertRaises(RuntimeError):
            list(iter_audio([audio_event(b'\0\0'), end_event(error=True)], 100))
        with self.assertRaises(ValueError):
            list(iter_audio([audio_event(b'\0\0' * 20), end_event()], 10))
