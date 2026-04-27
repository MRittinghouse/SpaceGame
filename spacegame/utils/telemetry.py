"""Opt-in telemetry for playtest baseline measurement.

Off by default. Set SPACEGAME_TELEMETRY=1 to enable. Output goes to
logs/telemetry/<session_id>.jsonl (one JSON object per line). Set
SPACEGAME_TELEMETRY_DIR to override the output directory (used in tests).

Importing this module has no side effects — no directories are created,
no files are opened. The output directory is created lazily on the first
enabled write.
"""

import datetime
import json
import os
from pathlib import Path
from typing import Optional

from spacegame.utils.logger import logger

# Module-level session state — reset between tests via _session_id/_session_path
_session_id: Optional[str] = None
_session_path: Optional[Path] = None


def is_enabled() -> bool:
    """Return True when SPACEGAME_TELEMETRY is set to a truthy value.

    Returns:
        True if telemetry is enabled.
    """
    return os.environ.get("SPACEGAME_TELEMETRY", "0").strip() == "1"


def current_session_path() -> Optional[Path]:
    """Return the path of the current session JSONL file, or None if not yet written.

    Returns:
        Path to current session file, or None if no write has occurred this session.
    """
    return _session_path


def record_event(event_type: str, **payload: object) -> None:
    """Append one JSON event line to the current session JSONL file.

    No-op when telemetry is disabled. On serialization or I/O errors,
    logs a warning and returns without raising.

    Args:
        event_type: Short string identifying the event (e.g. "anchor_card_clicked").
        **payload: Arbitrary key-value pairs merged into the event object.
    """
    if not is_enabled():
        return

    global _session_id, _session_path

    # Build the event object before touching the filesystem
    now = datetime.datetime.now(datetime.timezone.utc)
    session = _get_or_create_session_id()

    event: dict[str, object] = {
        "event_type": event_type,
        "timestamp_iso": now.isoformat(),
        "session_id": session,
    }
    event.update(payload)

    try:
        line = json.dumps(event)
    except (TypeError, ValueError) as exc:
        logger.warning(f"telemetry: could not serialize event '{event_type}': {exc}")
        return

    output_path = _get_session_path(session)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        _session_path = output_path
    except OSError as exc:
        logger.warning(f"telemetry: could not write event '{event_type}': {exc}")


def _get_or_create_session_id() -> str:
    """Return the current session ID, creating it if this is the first call.

    Returns:
        Session ID string in YYYYMMDD_HHMMSS_<pid> format.
    """
    global _session_id
    if _session_id is None:
        now = datetime.datetime.now()
        pid = os.getpid()
        _session_id = f"{now.strftime('%Y%m%d_%H%M%S')}_{pid}"
    return _session_id


def _get_session_path(session_id: str) -> Path:
    """Resolve the JSONL output path for the given session ID.

    Args:
        session_id: The session identifier.

    Returns:
        Absolute path to the session JSONL file.
    """
    output_dir_env = os.environ.get("SPACEGAME_TELEMETRY_DIR")
    if output_dir_env:
        base = Path(output_dir_env)
    else:
        base = Path("logs") / "telemetry"
    return base / f"{session_id}.jsonl"
