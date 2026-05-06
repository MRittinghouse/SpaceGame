"""Drift-protection tests for run.py launcher dependency check.

The launcher reads ``[project].dependencies`` from pyproject.toml at startup
(see ``run.load_runtime_dependencies``) so the launcher and project metadata
cannot diverge. These tests guard the integrity of that pipeline: every
declared dependency must resolve to an import name that's actually
importable in the dev environment.

Background: numpy was added as a runtime dependency in pyproject.toml but
the launcher's hardcoded ``required_packages`` list was not updated. The
launcher reported "All dependencies installed" while numpy was missing,
and the game crashed on first combat entry. The fix makes pyproject.toml
the source of truth; these tests make sure the dist→import-name mapping
(``run._DIST_TO_IMPORT_NAME``) stays correct as new deps are added.
"""

import importlib

import run


class TestLoadRuntimeDependencies:
    def test_returns_dist_and_import_name_pairs(self) -> None:
        deps = run.load_runtime_dependencies()

        assert deps, "pyproject.toml [project].dependencies should not be empty"
        for entry in deps:
            assert isinstance(entry, tuple) and len(entry) == 2
            dist_name, import_name = entry
            assert dist_name and isinstance(dist_name, str)
            assert import_name and isinstance(import_name, str)

    def test_strips_pep508_version_specifiers(self) -> None:
        # Entries in pyproject look like "numpy>=2.0" — the loader must
        # return the bare distribution name, never a spec fragment.
        deps = run.load_runtime_dependencies()
        for dist_name, _ in deps:
            for char in (">", "<", "=", "!", "~", " ", ";", "["):
                assert char not in dist_name, (
                    f"dist_name {dist_name!r} should not contain {char!r}"
                )

    def test_every_declared_dependency_imports_in_dev_env(self) -> None:
        # The dev environment installs every runtime dep, so each resolved
        # import_name must succeed. Failure means either (a) the user has
        # an out-of-sync venv (run `uv sync --extra dev` or `pip install -e
        # .[dev]`), or (b) a new dependency was added with an import name
        # that does not match the default `dash→underscore` rule, and
        # `run._DIST_TO_IMPORT_NAME` needs an entry for it.
        deps = run.load_runtime_dependencies()
        unresolved: list[tuple[str, str, str]] = []
        for dist_name, import_name in deps:
            try:
                importlib.import_module(import_name)
            except ImportError as e:
                unresolved.append((dist_name, import_name, str(e)))

        assert not unresolved, (
            "Declared runtime dependencies failed to import. Either install "
            "them in your venv, or add a dist→import-name override to "
            "run._DIST_TO_IMPORT_NAME:\n"
            + "\n".join(
                f"  {dist}: tried `import {imp}` ({err})" for dist, imp, err in unresolved
            )
        )

    def test_dist_to_import_overrides_resolve_to_known_packages(self) -> None:
        # Sanity check on the static override map — every override should
        # name an importable module. If one rots away (e.g., we drop
        # pygame-ce), this test fails so the override gets cleaned up.
        for dist_name, import_name in run._DIST_TO_IMPORT_NAME.items():
            try:
                importlib.import_module(import_name)
            except ImportError as e:
                raise AssertionError(
                    f"Override {dist_name!r} → {import_name!r} in "
                    f"run._DIST_TO_IMPORT_NAME does not resolve: {e}"
                ) from e
