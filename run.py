"""
Aurelia: A Ledger of Stars - Launch Script

Professional launcher with environment detection, dependency checking,
and helpful error messages.
"""

import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Optional, Tuple

# Map PyPI dist names to importable module names where they differ.
# pip dist names use hyphens; Python imports use underscores. The two are
# mostly interchangeable, except where the project name and module name are
# semantically unrelated (the pygame-ce → pygame case).
_DIST_TO_IMPORT_NAME: dict[str, str] = {
    "pygame-ce": "pygame",
    "pygame-gui": "pygame_gui",
}


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header() -> None:
    """Print the game header."""
    print(f"\n{Colors.CYAN}{Colors.BOLD}")
    print("=" * 60)
    print("  +=====================================================+")
    print("  |     AURELIA: A LEDGER OF STARS                    |")
    print("  |     A Narrative-Driven Space Trading RPG          |")
    print("  +=====================================================+")
    print("=" * 60)
    print(f"{Colors.ENDC}\n")


def print_success(message: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}[OK] {message}{Colors.ENDC}")


def print_info(message: str) -> None:
    """Print info message."""
    print(f"{Colors.CYAN}[i] {message}{Colors.ENDC}")


def print_warning(message: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}[!] {message}{Colors.ENDC}")


def print_error(message: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}[X] {message}{Colors.ENDC}")


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.resolve()


def check_python_version() -> bool:
    """
    Check if Python version is compatible.

    Returns:
        True if version is compatible, False otherwise
    """
    print_info("Checking Python version...")

    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    print(f"  Python version: {version_str}")

    if version.major != 3:
        print_error("Python 3 is required!")
        return False

    if version.minor < 11:
        print_error("Python 3.11 or higher is required!")
        print(f"  Current version: {version_str}")
        print(f"  Please upgrade to Python 3.11, 3.12, or 3.13")
        return False

    if version.minor >= 14:
        print_warning(f"Python {version_str} may not be fully supported yet.")
        print_warning("Python 3.13 is recommended for best compatibility.")
        print_info("Attempting to continue anyway...")
    else:
        print_success(f"Python {version_str} - Compatible!")

    return True


def find_python_executable() -> Tuple[Optional[Path], str]:
    """
    Find the best Python executable to use.

    Returns:
        Tuple of (path to python executable, description)
    """
    project_root = get_project_root()

    # Check for virtual environment
    venv_paths = [
        project_root / ".venv" / "Scripts" / "python.exe",  # Windows
        project_root / ".venv" / "bin" / "python",  # Unix/macOS
        project_root / "venv" / "Scripts" / "python.exe",  # Windows alt
        project_root / "venv" / "bin" / "python",  # Unix/macOS alt
    ]

    for venv_python in venv_paths:
        if venv_python.exists():
            return venv_python, "virtual environment"

    # Fall back to system Python
    return Path(sys.executable), "system Python"


def load_runtime_dependencies() -> list[tuple[str, str]]:
    """Read [project].dependencies from pyproject.toml.

    Returns:
        A list of (dist_name, import_name) pairs. ``dist_name`` is what pip
        installs (e.g., ``pygame-ce``, ``numpy``); ``import_name`` is what
        Python imports (e.g., ``pygame``). The two differ for some packages,
        so dependency checking needs both.

    Raises:
        FileNotFoundError: pyproject.toml does not exist at the project root.
        KeyError: pyproject.toml is missing the [project].dependencies table.
        ValueError: a dependency string cannot be parsed for its name.
    """
    pyproject = get_project_root() / "pyproject.toml"
    with open(pyproject, "rb") as f:
        data = tomllib.load(f)

    deps_raw = data["project"]["dependencies"]
    pairs: list[tuple[str, str]] = []
    for spec in deps_raw:
        # PEP 508 dependency string: name[extras] (op version)? (; markers)?
        # We only need the leading distribution name; everything after is
        # version specifier or environment marker.
        match = re.match(r"^[A-Za-z0-9_.\-]+", spec)
        if not match:
            raise ValueError(f"Could not parse dependency name from: {spec!r}")
        dist_name = match.group(0)
        import_name = _DIST_TO_IMPORT_NAME.get(dist_name, dist_name.replace("-", "_"))
        pairs.append((dist_name, import_name))
    return pairs


def check_dependencies(python_exe: Path) -> bool:
    """
    Check if required dependencies are installed.

    The required-packages list is derived from pyproject.toml's
    ``[project].dependencies`` so the launcher and the project metadata
    cannot silently drift apart.

    Args:
        python_exe: Path to Python executable

    Returns:
        True if all dependencies are installed, False otherwise
    """
    print_info("Checking dependencies...")

    try:
        required = load_runtime_dependencies()
    except (FileNotFoundError, KeyError, ValueError) as e:
        print_error(f"Could not read dependencies from pyproject.toml: {e}")
        return False

    missing_dist_names: list[str] = []

    for dist_name, import_name in required:
        try:
            result = subprocess.run(
                [str(python_exe), "-c", f"import {import_name}"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                print_success(f"{dist_name} is installed")
            else:
                missing_dist_names.append(dist_name)
                print_error(f"{dist_name} is NOT installed")
        except Exception as e:
            print_warning(f"Could not check {dist_name}: {e}")
            missing_dist_names.append(dist_name)

    if missing_dist_names:
        print_error("\nMissing required dependencies!")
        print("\nTo install missing dependencies, run:")
        print(f"{Colors.YELLOW}  pip install {' '.join(missing_dist_names)}{Colors.ENDC}")
        all_dist_names = " ".join(dist for dist, _ in required)
        print("\nOr install all dependencies with:")
        print(f"{Colors.YELLOW}  pip install {all_dist_names}{Colors.ENDC}")
        return False

    print_success("All dependencies are installed!")
    return True


def check_project_structure() -> bool:
    """
    Verify the project structure is intact.

    Returns:
        True if structure is valid, False otherwise
    """
    print_info("Checking project structure...")

    project_root = get_project_root()
    required_files = [
        "spacegame/__init__.py",
        "spacegame/main.py",
        "spacegame/config.py",
        "spacegame/engine/game.py",
    ]

    missing_files = []
    for file_path in required_files:
        full_path = project_root / file_path
        if not full_path.exists():
            missing_files.append(file_path)
            print_error(f"Missing: {file_path}")
        else:
            print_success(f"Found: {file_path}")

    if missing_files:
        print_error("\nProject structure is incomplete!")
        print_error("Some core files are missing.")
        return False

    print_success("Project structure is valid!")
    return True


def launch_game(python_exe: Path) -> int:
    """
    Launch the game.

    Args:
        python_exe: Path to Python executable

    Returns:
        Exit code from the game
    """
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print_info("Launching Aurelia: A Ledger of Stars...")
    print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")

    # Add project root to Python path
    project_root = get_project_root()
    sys.path.insert(0, str(project_root))

    try:
        # Import and run the game
        from spacegame.main import main

        # Run the game
        main()
        return 0

    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Game interrupted by user{Colors.ENDC}")
        return 0
    except Exception as e:
        print_error(f"\nGame crashed with error:")
        print(f"{Colors.RED}{type(e).__name__}: {e}{Colors.ENDC}")
        import traceback
        print(f"\n{Colors.RED}Traceback:{Colors.ENDC}")
        traceback.print_exc()
        return 1


def show_help() -> None:
    """Show help information."""
    print_header()
    print("Usage: python run.py [OPTIONS]\n")
    print("Options:")
    print("  --help, -h     Show this help message")
    print("  --check        Check environment without launching game")
    print("  --version      Show game version")
    print("\nExamples:")
    print("  python run.py              Launch the game")
    print("  python run.py --check      Verify installation")
    print()


def show_version() -> None:
    """Show version information."""
    print_header()
    print_info("Aurelia: A Ledger of Stars - Version 0.1.0 (Alpha)")
    print_info("Built with PyGame")
    print()


def run_environment_check() -> bool:
    """
    Run all environment checks.

    Returns:
        True if all checks pass, False otherwise
    """
    print_header()
    print(f"{Colors.BOLD}Environment Check{Colors.ENDC}\n")

    # Check Python version
    if not check_python_version():
        return False
    print()

    # Find Python executable
    python_exe, source = find_python_executable()
    print_info(f"Using Python from: {source}")
    print(f"  Path: {python_exe}\n")

    # Check project structure
    if not check_project_structure():
        return False
    print()

    # Check dependencies
    if not check_dependencies(python_exe):
        return False
    print()

    print(f"{Colors.GREEN}{Colors.BOLD}[OK] All checks passed!{Colors.ENDC}\n")
    return True


def main() -> int:
    """
    Main entry point for the launcher.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Parse command line arguments
    args = sys.argv[1:]

    if "--help" in args or "-h" in args:
        show_help()
        return 0

    if "--version" in args:
        show_version()
        return 0

    if "--check" in args:
        success = run_environment_check()
        return 0 if success else 1

    # Run full environment check
    if not run_environment_check():
        print_error("Environment check failed!")
        print_info("Run 'python run.py --help' for more information")
        return 1

    # Find Python executable
    python_exe, _ = find_python_executable()

    # Launch the game
    exit_code = launch_game(python_exe)

    # Goodbye message
    if exit_code == 0:
        print(f"\n{Colors.CYAN}Thank you for playing Aurelia: A Ledger of Stars!{Colors.ENDC}")
    else:
        print(f"\n{Colors.RED}Game exited with errors{Colors.ENDC}")

    return exit_code


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Launcher interrupted{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print_error(f"Launcher error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
