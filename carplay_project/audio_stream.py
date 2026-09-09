"""Versioned audio events: PCM chunks followed by an explicit done/error event."""

import base64
import json

CONTENT_TYPE = "application/x-ndjson"
STREAM_VERSION = "1"
CHUNK_BYTES = 4096
SAMPLE_RATE = 22050
MAX_LINE_BYTES = 8192


def audio_event(pcm):
    return (json.dumps({"type": "audio", "data": base64.b64encode(pcm).decode("ascii")}) + "\n").encode()


def end_event(error=False):
    return (json.dumps({"type": "error" if error else "done"}) + "\n").encode()


def iter_audio(chunks, max_bytes):
    """Handle arbitrary HTTP fragmentation and detect truncated/error streams."""
    buffer = bytearray()
    total = 0
    done = False
    for chunk in chunks:
        buffer.extend(chunk)
        while b"\n" in buffer:
            line, _, remainder = buffer.partition(b"\n")
            buffer = bytearray(remainder)
            if done or len(line) > MAX_LINE_BYTES:
                raise ValueError("Invalid audio stream framing")
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError("Invalid audio event")
            kind = event.get("type")
            if kind == "error":
                raise RuntimeError("Speech synthesis failed during streaming")
            if kind == "done":
                if not total:
                    raise ValueError("Empty audio stream")
                done = True
            elif kind == "audio":
                data = event.get("data")
                if not isinstance(data, str):
                    raise ValueError("Invalid audio payload")
                pcm = base64.b64decode(data, validate=True)
                total += len(pcm)
                if not 0 < len(pcm) <= CHUNK_BYTES or len(pcm) % 2 or total > max_bytes:
                    raise ValueError("Invalid or oversized PCM audio")
                yield pcm
            else:
                raise ValueError("Unknown audio event")
        if len(buffer) > MAX_LINE_BYTES:
            raise ValueError("Audio event is too large")
    if buffer or not done:
        raise ValueError("Audio stream ended before completion")
