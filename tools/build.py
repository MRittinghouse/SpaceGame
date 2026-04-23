"""Build script for the Aurelia: A Ledger of Stars distribution.

Runs tests, then invokes PyInstaller to produce a standalone executable.

Usage:
    python -m tools.build              # Full build (tests + PyInstaller)
    python -m tools.build --skip-tests # Skip tests, just build
"""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = PROJECT_ROOT / "spacegame.spec"
# PyInstaller emits under the product name declared in spacegame.spec (Aurelia),
# not the repo folder name (SpaceGame). Keep this in sync with the spec.
DIST_DIR = PROJECT_ROOT / "dist" / "Aurelia"
EXE_NAME = "Aurelia.exe"
ICON_PATH = PROJECT_ROOT / "spacegame" / "data" / "assets" / "images" / "icon.ico"


def _run(cmd: list[str], description: str) -> bool:
    """Run a command, printing status. Returns True on success."""
    print(f"\n{'=' * 60}")
    print(f"  {description}")
    print(f"{'=' * 60}\n")
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(f"\n  FAILED: {description} (exit code {result.returncode})")
        return False
    return True


def _get_dir_size(path: Path) -> int:
    """Get total size of a directory in bytes."""
    total = 0
    for f in path.rglob("*"):
        if f.is_file():
            total += f.stat().st_size
    return total


def _format_size(size_bytes: int) -> str:
    """Format bytes as human-readable string."""
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def main() -> int:
    """Run the full build pipeline."""
    parser = argparse.ArgumentParser(description="Build Aurelia distribution.")
    parser.add_argument(
        "--skip-tests", action="store_true", help="Skip running tests before building."
    )
    args = parser.parse_args()

    print("Aurelia Build Pipeline")
    print(f"  Project: {PROJECT_ROOT}")
    print(f"  Spec:    {SPEC_FILE}")

    # Step 1: Generate icon if missing
    if not ICON_PATH.exists():
        print("\nGenerating game icon...")
        if not _run([sys.executable, "-m", "tools.generate_icon"], "Generate icon"):
            return 1

    # Step 2: Run tests
    if not args.skip_tests:
        if not _run([sys.executable, "-m", "pytest", "--tb=short", "-q"], "Run tests"):
            print("\nBuild aborted: tests failed.")
            return 1
    else:
        print("\n  Skipping tests (--skip-tests)")

    # Step 3: Check PyInstaller is installed
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("\nERROR: PyInstaller not installed. Run: pip install pyinstaller")
        return 1

    # Step 4: Run PyInstaller
    if not _run(
        [sys.executable, "-m", "PyInstaller", str(SPEC_FILE), "--noconfirm"],
        "PyInstaller build",
    ):
        return 1

    # Step 5: Report results
    if DIST_DIR.exists():
        total_size = _get_dir_size(DIST_DIR)
        file_count = sum(1 for f in DIST_DIR.rglob("*") if f.is_file())
        exe_path = DIST_DIR / EXE_NAME

        print(f"\n{'=' * 60}")
        print("  BUILD COMPLETE")
        print(f"{'=' * 60}")
        print(f"  Artifact:   {DIST_DIR}")
        print(f"  Executable: {exe_path}")
        print(f"  Total size: {_format_size(total_size)}")
        print(f"  File count: {file_count}")
        print(f"  Exe exists: {exe_path.exists()}")
    else:
        print(f"\nWARNING: Expected output not found at {DIST_DIR}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
