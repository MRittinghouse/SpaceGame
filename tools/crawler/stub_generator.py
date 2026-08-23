"""Regression pytest stub generator for the play-harness crawler.

Given a ``CrashRecord``, emit a runnable pytest file into
``tools/crawler/generated_stubs/`` that reproduces the crash by driving the
crawler with the recorded seed and action index. The generated file is not
placed under ``tests/`` — humans triage and move it into the real suite once
they've confirmed the crash is worth pinning.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from tools.crawler.crash_record import CrashRecord

STUBS_DIR = Path(__file__).resolve().parent / "generated_stubs"


def generated_stubs_dir() -> Path:
    """Return the directory where regression stubs are emitted (mkdir on demand)."""
    STUBS_DIR.mkdir(parents=True, exist_ok=True)
    (STUBS_DIR / "__init__.py").touch(exist_ok=True)
    return STUBS_DIR


def stub_filename(record: CrashRecord) -> str:
    """Return the filename used for a given crash record's stub."""
    return f"test_regression_{record.signature}.py"


def render_stub(record: CrashRecord) -> str:
    """Render the .py source string for a regression stub.

    Args:
        record: The dedup'd CrashRecord to reproduce.

    Returns:
        The rendered stub source. Includes a pytest-runnable function.
    """
    body = textwrap.dedent(
        f'''\
        """Auto-generated regression stub for signature {record.signature}.

        Original crash: {record.exception_class}
        Oracle: {record.oracle}
        State at crash: {record.state_at_crash}
        First seed: {record.first_seed}
        First action index: {record.first_action_index}
        """

        from __future__ import annotations

        from tools.crawler.crawler import Crawler


        def test_regression_{record.signature}() -> None:
            """Reproduce the recorded crash at the recorded seed+index."""
            crawler = Crawler(seed={record.first_seed}, actions={record.first_action_index + 1})
            reproduced = crawler.replay(
                seed={record.first_seed},
                up_to_action_index={record.first_action_index},
            )
            assert reproduced is not None, (
                "Expected crash signature {record.signature} not reproduced"
            )
            assert reproduced.signature == "{record.signature}", (
                f"Expected signature {record.signature}, got {{reproduced.signature}}"
            )
        '''
    )
    return body


def write_stub(record: CrashRecord, target_dir: Path | None = None) -> Path:
    """Write the stub source for ``record`` to disk.

    Args:
        record: The crash record.
        target_dir: Optional override directory. Defaults to ``STUBS_DIR``.

    Returns:
        The Path of the written file.
    """
    if target_dir is None:
        target_dir = generated_stubs_dir()
    else:
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "__init__.py").touch(exist_ok=True)
    path = target_dir / stub_filename(record)
    path.write_text(render_stub(record), encoding="utf-8")
    return path
