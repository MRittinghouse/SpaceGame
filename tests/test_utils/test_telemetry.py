"""Tests for spacegame.utils.telemetry — opt-in JSONL event recorder."""

import builtins
import json
import sys


def _reload_telemetry(monkeypatch, env_value: str | None, tmp_dir: str | None = None):
    """Reload the telemetry module with a fresh environment.

    Args:
        monkeypatch: pytest monkeypatch fixture.
        env_value: Value for SPACEGAME_TELEMETRY, or None to unset.
        tmp_dir: If provided, overrides SPACEGAME_TELEMETRY_DIR.

    Returns:
        Freshly-imported telemetry module.
    """
    if env_value is None:
        monkeypatch.delenv("SPACEGAME_TELEMETRY", raising=False)
    else:
        monkeypatch.setenv("SPACEGAME_TELEMETRY", env_value)

    if tmp_dir is None:
        monkeypatch.delenv("SPACEGAME_TELEMETRY_DIR", raising=False)
    else:
        monkeypatch.setenv("SPACEGAME_TELEMETRY_DIR", tmp_dir)

    # Remove cached module so env changes take effect
    for key in list(sys.modules.keys()):
        if "spacegame.utils.telemetry" in key:
            del sys.modules[key]

    import spacegame.utils.telemetry as tel

    # Reset module-level state between tests
    tel._session_id = None  # type: ignore[attr-defined]
    tel._session_path = None  # type: ignore[attr-defined]
    return tel


class TestTelemetryDisabled:
    """Telemetry off by default — all public API is no-op."""

    def test_disabled_when_env_unset(self, monkeypatch, tmp_path):
        tel = _reload_telemetry(monkeypatch, None, str(tmp_path))
        assert tel.is_enabled() is False

    def test_disabled_when_env_zero(self, monkeypatch, tmp_path):
        tel = _reload_telemetry(monkeypatch, "0", str(tmp_path))
        assert tel.is_enabled() is False

    def test_record_event_no_file_created_when_disabled(self, monkeypatch, tmp_path):
        tel = _reload_telemetry(monkeypatch, None, str(tmp_path))
        tel.record_event("test_event", foo="bar")
        # No JSONL file should exist under tmp_path
        files = list(tmp_path.rglob("*.jsonl"))
        assert files == [], f"Unexpected files created: {files}"

    def test_current_session_path_none_when_disabled(self, monkeypatch, tmp_path):
        tel = _reload_telemetry(monkeypatch, None, str(tmp_path))
        assert tel.current_session_path() is None


class TestTelemetryEnabled:
    """Telemetry on with SPACEGAME_TELEMETRY=1."""

    def test_enabled_when_env_one(self, monkeypatch, tmp_path):
        tel = _reload_telemetry(monkeypatch, "1", str(tmp_path))
        assert tel.is_enabled() is True

    def test_record_event_writes_jsonl(self, monkeypatch, tmp_path):
        tel = _reload_telemetry(monkeypatch, "1", str(tmp_path))
        tel.record_event("anchor_card_clicked", anchor_id="crimson_wreckers_guild")

        files = list(tmp_path.rglob("*.jsonl"))
        assert len(files) == 1, f"Expected 1 JSONL file, got {files}"

        line = files[0].read_text(encoding="utf-8").strip()
        obj = json.loads(line)
        assert obj["event_type"] == "anchor_card_clicked"
        assert obj["anchor_id"] == "crimson_wreckers_guild"

    def test_event_schema_has_required_fields(self, monkeypatch, tmp_path):
        tel = _reload_telemetry(monkeypatch, "1", str(tmp_path))
        tel.record_event("test_event", key="value")

        files = list(tmp_path.rglob("*.jsonl"))
        obj = json.loads(files[0].read_text(encoding="utf-8").strip())

        assert "event_type" in obj, "Missing event_type"
        assert "timestamp_iso" in obj, "Missing timestamp_iso"
        assert "session_id" in obj, "Missing session_id"
        assert "key" in obj, "Missing payload field 'key'"
        assert obj["key"] == "value"

    def test_two_events_append_two_lines(self, monkeypatch, tmp_path):
        tel = _reload_telemetry(monkeypatch, "1", str(tmp_path))
        tel.record_event("event_one", x=1)
        tel.record_event("event_two", x=2)

        files = list(tmp_path.rglob("*.jsonl"))
        assert len(files) == 1
        lines = [l for l in files[0].read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 2, f"Expected 2 lines, got {lines}"

        obj1 = json.loads(lines[0])
        obj2 = json.loads(lines[1])
        assert obj1["event_type"] == "event_one"
        assert obj2["event_type"] == "event_two"

    def test_each_line_parses_as_json(self, monkeypatch, tmp_path):
        tel = _reload_telemetry(monkeypatch, "1", str(tmp_path))
        for i in range(5):
            tel.record_event(f"event_{i}", index=i)

        files = list(tmp_path.rglob("*.jsonl"))
        for raw_line in files[0].read_text(encoding="utf-8").splitlines():
            if raw_line.strip():
                json.loads(raw_line)  # must not raise

    def test_current_session_path_set_after_first_write(self, monkeypatch, tmp_path):
        tel = _reload_telemetry(monkeypatch, "1", str(tmp_path))
        assert tel.current_session_path() is None  # before first write
        tel.record_event("ping")
        path = tel.current_session_path()
        assert path is not None
        assert path.exists()
        assert path.suffix == ".jsonl"

    def test_session_id_format(self, monkeypatch, tmp_path):
        """Session ID should be YYYYMMDD_HHMMSS_<pid>."""
        tel = _reload_telemetry(monkeypatch, "1", str(tmp_path))
        tel.record_event("ping")
        path = tel.current_session_path()
        assert path is not None
        name = path.stem  # filename without .jsonl
        parts = name.split("_")
        assert len(parts) == 3, f"Unexpected session_id format: {name}"
        date_part, time_part, pid_part = parts
        assert len(date_part) == 8 and date_part.isdigit()
        assert len(time_part) == 6 and time_part.isdigit()
        assert pid_part.isdigit()


class TestTelemetryRobustness:
    """Error handling — must not raise, must log warning."""

    def test_non_serializable_payload_does_not_raise(self, monkeypatch, tmp_path, caplog):
        import logging

        tel = _reload_telemetry(monkeypatch, "1", str(tmp_path))

        with caplog.at_level(logging.WARNING, logger="spacegame"):
            tel.record_event("bad_payload", obj=object())  # object() is not JSON-serializable

        # Must not have raised; warning should be logged
        assert any(
            "serial" in r.message.lower() or "warn" in r.levelname.lower() for r in caplog.records
        )

    def test_io_error_does_not_raise(self, monkeypatch, tmp_path, caplog):
        """Simulated I/O error on append must log a warning and not raise."""
        import logging

        tel = _reload_telemetry(monkeypatch, "1", str(tmp_path))

        real_open = builtins.open

        def _failing_open(path, *args, **kwargs):
            # Intercept append opens going to our telemetry directory
            if "a" in str(args[0] if args else kwargs.get("mode", "")) or (
                str(path).endswith(".jsonl")
            ):
                raise OSError("simulated disk full")
            return real_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", _failing_open)

        with caplog.at_level(logging.WARNING, logger="spacegame"):
            tel.record_event("io_error_test", x=1)

        # Must not have raised; a warning should be present
        warning_msgs = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warning_msgs) >= 1, "Expected at least one warning on IO error"


class TestTelemetryNoImportSideEffects:
    """Importing the module must not create files or directories."""

    def test_import_does_not_create_files(self, monkeypatch, tmp_path):
        _reload_telemetry(monkeypatch, "1", str(tmp_path))
        # Just imported — no record_event called yet
        files = list(tmp_path.rglob("*"))
        assert files == [], f"Import created unexpected files: {files}"
