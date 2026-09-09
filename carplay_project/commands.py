"""Shared validation for commands crossing the assistant API boundary."""

ALLOWED_ACTIONS = {
    "none", "volume_up", "volume_down", "volume_set", "music_next", "music_prev",
    "music_toggle", "music_play", "open_music", "open_camera", "open_map",
    "open_home", "navigate_to",
}
MAX_QUERY_LENGTH = 300
MAX_SPEECH_LENGTH = 500


def validate_command(data, require_speech=False):
    if not isinstance(data, dict):
        raise ValueError("Command must be an object")
    action = data.get("action")
    if not isinstance(action, str) or action not in ALLOWED_ACTIONS:
        raise ValueError("Unknown action")
    args = data.get("args", {})
    if not isinstance(args, dict):
        raise ValueError("Arguments must be an object")
    clean_args = {}
    if action == "volume_set":
        percent = args.get("percent")
        if type(percent) is not int or not 0 <= percent <= 100:
            raise ValueError("Volume must be an integer from 0 to 100")
        clean_args["percent"] = percent
    elif action in ("music_play", "navigate_to"):
        key = "query" if action == "music_play" else "destination"
        value = args.get(key)
        if not isinstance(value, str) or not 0 < len(value.strip()) <= MAX_QUERY_LENGTH:
            raise ValueError(f"Invalid {key}")
        clean_args[key] = value.strip()
    result = {"action": action, "args": clean_args}
    if require_speech:
        say = data.get("say")
        if not isinstance(say, str) or not 0 < len(say.strip()) <= MAX_SPEECH_LENGTH:
            raise ValueError("Invalid speech")
        result["say"] = say.strip()
    return result
