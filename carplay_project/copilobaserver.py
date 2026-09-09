"""Flask API for one bounded voice-assistant job at a time per server process."""

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import atexit
import base64
import hmac
import json
import logging
from pathlib import Path
import subprocess
import tempfile
import threading

from flask import Flask, Response, request

from carplay_project import config
from carplay_project.backend.audio import InvalidAudio, validate_audio
from carplay_project.backend.speech import PiperSynthesizer
from carplay_project.audio_stream import CONTENT_TYPE, STREAM_VERSION, audio_event, end_event
from carplay_project.backend.language import ask_copiloba
from carplay_project.backend.transcription import Transcriber
from carplay_project.commands import validate_command


def create_app(transcriber=None, synthesizer=None):
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=config.MAX_UPLOAD_BYTES,
                      API_TOKEN=config.COPILOBA_API_TOKEN)
    transcriber = transcriber if transcriber is not None else Transcriber()
    synthesizer = synthesizer if synthesizer is not None else PiperSynthesizer()
    admission = threading.Lock()
    app.extensions["transcriber"] = transcriber
    app.extensions["admission"] = admission
    app.extensions["synthesizer"] = synthesizer
    atexit.register(transcriber.close)
    atexit.register(synthesizer.close)

    @app.errorhandler(413)
    def too_large(error):
        return {"error": "Audio upload is too large"}, 413

    @app.errorhandler(400)
    def bad_request(error):
        return {"error": "Malformed upload"}, 400

    @app.get("/health")
    def health():
        # Liveness only: models load lazily and are checked by actual requests.
        return {"status": "ok"}

    @app.post("/ask_audio")
    def ask_audio():
        token = app.config["API_TOKEN"]
        if token and not hmac.compare_digest(
            request.headers.get("Authorization", "").encode(), f"Bearer {token}".encode()
        ):
            return {"error": "Unauthorized"}, 401
        if not admission.acquire(blocking=False):
            return {"error": "Assistant is busy; try again shortly"}, 503, {"Retry-After": "1"}
        audio_stream = None
        handed_off = False
        released = False

        def finish():
            nonlocal released
            if not released:
                released = True
                try:
                    if audio_stream is not None:
                        audio_stream.close()
                finally:
                    admission.release()

        try:
            if "audio" not in request.files:
                return {"error": "No audio file"}, 400
            # Never use the client filename; isolate every request and clean up on errors.
            with tempfile.TemporaryDirectory(prefix="copiloba-upload-") as directory:
                path = Path(directory) / "recording.wav"
                request.files["audio"].save(path)
                validate_audio(path)
                prompt = transcriber.transcribe(path)
            if not prompt.strip():
                return {"error": "Could not hear anything"}, 400
            command = validate_command(ask_copiloba(prompt), require_speech=True)
            audio_stream = synthesizer.stream(command["say"])
            # Preflight only the first PCM chunk: startup failures still return JSON.
            first_chunk = next(audio_stream)
            encoded = base64.b64encode(json.dumps(
                {"action": command["action"], "args": command["args"]}
            ).encode()).decode("ascii")
            def events():
                try:
                    yield audio_event(first_chunk)
                    for chunk in audio_stream:
                        yield audio_event(chunk)
                    yield end_event()
                except (OSError, RuntimeError, ValueError, TimeoutError, EOFError):
                    app.logger.exception("Speech stream failed")
                    yield end_event(error=True)
                finally:
                    finish()

            response = Response(events(), mimetype=CONTENT_TYPE, headers={
                "X-Copiloba-Action": encoded, "X-Copiloba-Stream-Version": STREAM_VERSION,
                "Cache-Control": "no-store", "X-Accel-Buffering": "no",
            })
            response.call_on_close(finish)
            handed_off = True
            return response
        except InvalidAudio as exc:
            return {"error": str(exc)}, 400
        except (TimeoutError, subprocess.TimeoutExpired):
            app.logger.warning("Voice processing timed out")
            return {"error": "Voice processing timed out; please try again"}, 504
        except (OSError, RuntimeError, ValueError, subprocess.SubprocessError, EOFError, StopIteration):
            app.logger.exception("Voice processing failed")
            return {"error": "Voice processing failed; please try again"}, 502
        finally:
            if not handed_off:
                finish()

    return app


app = create_app()

if __name__ == "__main__":
    from waitress import serve

    logging.basicConfig(level=logging.INFO)
    serve(app, host=config.BACKEND_HOST, port=config.BACKEND_PORT, threads=4,
          max_request_body_size=config.MAX_UPLOAD_BYTES)
