# Copiloba

![Copiloba](Copiloba%20splash.png)

An embedded Linux infotainment system built on the state-of-the-art development board STM32MP257F-DK

- Camera
- Map with GPS
- Spotify integration
- Communication with a custom Flask API backend for embedded AI functionalities
- AI powered voice commands
- Interface with real time sensors via OpenAMP 

### Demo Video [Here](https://www.youtube.com/watch?v=30z_-YydxKc)!

## Code layout

```text
carplay_project/
├── main.py                 # Dashboard entry point
├── config.py               # Shared .env configuration and asset paths
├── commands.py             # Shared command validation
├── copilobaserver.py        # Flask API and request admission
├── backend/                # Whisper process, Ollama, and Piper
├── services/
│   ├── copiloba_ai.py       # Microphone capture and backend communication
│   ├── navigation.py       # Geocoding and route requests
│   └── sensors.py          # OpenAMP/RPMsg sensor input
├── ui/
│   ├── window.py           # Main window and assistant command dispatch
│   ├── styles.py           # Shared GTK styles
│   ├── backgrounds.py      # Cached Cairo backgrounds
│   ├── screens/            # Camera, map, and Spotify screens
│   └── widgets/            # Clock, weather, Spotify card, and volume
└── media/                  # Bundled icons and images
```

## Configuration and launch

The dashboard runs on the STM32 board. The Flask backend runs on a separate
host with Whisper, Ollama, and Piper installed. Each host reads its own `.env`
from the repository root, regardless of the directory used to launch Python.
Exported environment variables take precedence over `.env`.

For a new clone, copy `.env.example` to `.env` and edit the settings for that
host. Keep an existing `.env` when updating your checkout. The local `.env`,
Spotify token cache, and generated files are ignored by Git.

On the **board**, install the Python dependencies in your application environment:

```sh
python -m pip install -r requirements-device.txt
python -m carplay_project.main
```

The board image must also provide PyGObject, Pycairo, GTK 3, GStreamer 1.0
(including V4L2, JPEG decoding, and `gtksink`), and OsmGpsMap 1.0 introspection
bindings. Runtime tools include `arecord`, `aplay`, `pactl`, `wpctl`, `pgrep`,
and `librespot`. These native dependencies are not installed by the requirements
file. The Pixel Operator fonts are in `carplay_project/pixel_operator/`.

Set `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, and the matching OAuth redirect
URI. Set `COPILOBA_SERVER_URL` to the backend host's `/ask_audio` URL, and adjust
the camera, microphone, RPMsg, and librespot settings to match your board.
Leave `AUDIO_SINK` empty to retain the current system audio sink. The sensor
service expects firmware exposing `/dev/ttyRPMSG0`; that firmware is not included.

Authorize Spotify explicitly before launching the dashboard when you need a new
token cache: `python -m carplay_project.spotify_login`. Follow the terminal URL
instructions; the dashboard itself never opens an interactive login prompt.
Cached tokens can refresh in the background during normal use.

On the **backend host**:

```sh
python -m pip install -r requirements-backend.txt
python -m carplay_project.copilobaserver
```

Install Ollama and pull the model selected by `OLLAMA_MODEL` (default `llama3`).
The backend requirements install Piper's Python API. Keep `PIPER_VOICE_MODEL`
pointing to the existing `es_AR-daniela-high.onnx`, with its matching
`es_AR-daniela-high.onnx.json` beside it. A separate `piper.exe` and `PIPER_EXEC`
setting are no longer used. The voice remains 22,050 Hz mono signed 16-bit PCM,
with the existing `length_scale=0.82` and 100 ms sentence pauses.
`WHISPER_MODEL` defaults to `base`, loaded on the backend CPU with int8 computation.
On Windows, single-quote model paths in `.env`, for example
`PIPER_VOICE_MODEL='C:\workspace\piper\voicemodels\es_AR-daniela-high.onnx'`.

The original direct script commands also work:
`python carplay_project/main.py` and `python carplay_project/copilobaserver.py`.
Dependency versions have not yet been locked against a fresh board installation.

## Reliability and API behavior

- The board accepts one assistant request at a time and disables the microphone
  button while it is busy. Recording and playback have process timeouts; HTTP
  calls have connect/read timeouts. Each request uses a private temporary directory.
- Spotify polling, token refresh, artwork processing, and playback commands share
  one background worker. Polls are deduplicated and command queues are bounded.
  System audio commands also run outside GTK. Closing the dashboard discards
  pending work and prevents late callbacks from updating destroyed widgets.
- Route searches ignore cancelled/stale results, and report network/route failures
  in the map screen. RPMsg disconnects close file descriptors and retry without an
  EOF busy loop; shutdown removes both retry timers and I/O watches.
- The backend admits one voice job per server process. Concurrent requests get
  `503` with `Retry-After`; the client does not automatically replay commands.
  Uploads default to a 2 MiB limit and must contain valid 16-bit mono/stereo PCM
  WAV audio at 8–48 kHz, no longer than 15 seconds. Client filenames are ignored.
- Whisper runs in a persistent child process. A timed-out inference terminates
  that process; the next request starts a fresh one. Its timeout includes initial
  model loading, so pre-download the model or increase `WHISPER_TIMEOUT` if needed.
- Invalid Ollama output falls back to validated keyword commands. Both server and
  client validate action names, argument types/ranges, and text lengths.
- Piper loads lazily into a persistent child process and reuses the same voice
  across successful requests. `PIPER_LOAD_TIMEOUT` bounds model loading;
  `PIPER_TIMEOUT` bounds cumulative waiting for synthesized audio, excluding time
  spent forwarding chunks to the client. Cancelled, failed, or hung streams discard
  the worker so the next request can start cleanly.
- Audio streams from Piper to HTTP to `aplay`; the client starts playing the first
  valid chunk while later chunks arrive. Piper generates audio per sentence, so a
  one-sentence reply still waits for that sentence's inference. Nonblocking pipe
  writes and a playback deadline prevent a stalled `aplay` from hanging the writer.
- Before sending headers, the server waits only for the first audio chunk. Early
  failures return JSON `502`/`504`; later failures send a stream error marker.
  The client kills playback on failure and detects a missing completion marker.
  Commands execute once when the first valid PCM reaches playback; a later audio
  failure cannot undo an action already executed, and no command is retried automatically.
- Set the same `COPILOBA_API_TOKEN` on both hosts to require bearer authentication.
  An empty value retains unauthenticated development access. The token does not
  encrypt HTTP traffic; use a trusted private connection or TLS when appropriate.

The backend script uses Waitress with four HTTP threads and one inference worker.
Run one server process on the model host; adding WSGI processes would create one
model and admission lock per process. `GET /health` reports server liveness, not
model readiness. All limits and timeouts are documented in `.env.example`.
HTTP read timeouts limit idle socket waits, rather than imposing a strict deadline
on DNS resolution or an entire multi-request operation.

### Streaming protocol

Update the backend and dashboard together: `/ask_audio` now returns
`application/x-ndjson` with `X-Copiloba-Stream-Version: 1`. The validated command
remains in the base64 JSON `X-Copiloba-Action` header. Each newline-delimited JSON
event is `{"type":"audio","data":"<base64 PCM>"}`, `{"type":"done"}`, or
`{"type":"error"}`. PCM chunks are at most 4 KiB, and `MAX_RESPONSE_BYTES` limits
the total decoded audio. Framing permits explicit failure/completion detection
while playing incrementally. Disable response buffering in any reverse proxy;
the application sends `X-Accel-Buffering: no` for proxies that support it.

## Software checks

These tests run without GTK, the board, downloaded models, or live service accounts:

```sh
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
```

The suite mocks device/service interfaces and uses real threads and child processes
to check queue limits, timeout recovery, cancellation, API validation, and cleanup.
