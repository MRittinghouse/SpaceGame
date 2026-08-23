"""Regression stub generator tests (QF-6, Task 11)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from tools.crawler.crash_record import CrashRecord
from tools.crawler.stub_generator import render_stub, write_stub


def _sample_record(signature: str = "abcdef1234567890") -> CrashRecord:
    return CrashRecord(
        signature=signature,
        exception_class="RuntimeError",
        first_seed=42,
        first_action_index=5,
        occurrence_count=1,
        action_trace=[("click", "UIButton['Go']@(100,200)")],
        full_traceback="Traceback (most recent call last):\n  ...\nRuntimeError: x",
        state_at_crash="GALAXY_MAP",
        oracle="exception",
    )


class TestRenderStub:
    def test_render_stub_contains_pytest_function(self) -> None:
        record = _sample_record()
        src = render_stub(record)
        assert "def test_regression_" in src
        assert record.signature in src
        assert "Crawler(seed=42" in src

    def test_render_stub_uses_replay_helper(self) -> None:
        record = _sample_record()
        src = render_stub(record)
        assert "replay(" in src
        assert "up_to_action_index=5" in src


class TestWriteStub:
    def test_write_stub_creates_file(self, tmp_path: Path) -> None:
        record = _sample_record()
        target = tmp_path / "stubs"
        path = write_stub(record, target_dir=target)
        assert path.exists()
        assert path.name == f"test_regression_{record.signature}.py"

    def test_regression_stub_generator_produces_runnable_pytest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The generated stub must be importable and expose a callable test.

        The stub calls ``Crawler.replay`` which normally boots a real Game;
        for this unit test we monkeypatch it to return ``None`` (representing
        a codebase where the crash no longer reproduces). The generated stub
        must then raise AssertionError per its 'would pass once fixed'
        contract.
        """
        record = _sample_record("f" * 16)
        target = tmp_path / "stubs"
        path = write_stub(record, target_dir=target)

        spec = importlib.util.spec_from_file_location(
            "generated_stub_test", str(path)
        )
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        func_name = f"test_regression_{record.signature}"
        assert hasattr(module, func_name)
        func = getattr(module, func_name)
        assert callable(func)

        # Replace Crawler with a lightweight double: __init__ is a no-op,
        # replay always returns None ("crash no longer reproduces").
        class _FakeCrawler:
            def __init__(self, *_args: object, **_kwargs: object) -> None:
                pass

            def replay(self, seed: int, up_to_action_index: int) -> None:
                return None

        monkeypatch.setattr(module, "Crawler", _FakeCrawler)
        with pytest.raises(AssertionError):
            func()

    def test_regression_stub_asserts_signature_match(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A stub whose replay returns a matching signature must pass."""
        record = _sample_record("e" * 16)
        target = tmp_path / "stubs"
        path = write_stub(record, target_dir=target)

        spec = importlib.util.spec_from_file_location(
            "generated_stub_test_pass", str(path)
        )
        assert spec is not None
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        class _FakeCrashResult:
            signature = record.signature

        class _FakeCrawler:
            def __init__(self, *_args: object, **_kwargs: object) -> None:
                pass

            def replay(self, seed: int, up_to_action_index: int) -> object:
                return _FakeCrashResult()

        monkeypatch.setattr(module, "Crawler", _FakeCrawler)
        func = getattr(module, f"test_regression_{record.signature}")
        # No exception raised.
        func()
