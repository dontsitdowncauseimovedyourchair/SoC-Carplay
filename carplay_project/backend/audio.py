"""Validate short PCM WAV uploads."""

import wave

from carplay_project import config


class InvalidAudio(ValueError):
    pass


def validate_audio(path):
    try:
        with wave.open(str(path), "rb") as audio:
            frames = audio.getnframes()
            rate = audio.getframerate()
            if (audio.getcomptype() != "NONE" or audio.getsampwidth() != 2
                    or audio.getnchannels() not in (1, 2) or not 8000 <= rate <= 48000
                    or not 0 < frames <= rate * config.MAX_RECORDING_SECONDS):
                raise InvalidAudio("Expected a short mono/stereo 16-bit PCM WAV recording")
            expected = frames * audio.getnchannels() * audio.getsampwidth()
            if len(audio.readframes(frames)) != expected:
                raise InvalidAudio("Truncated WAV recording")
    except (wave.Error, EOFError) as exc:
        raise InvalidAudio("Invalid WAV recording") from exc

