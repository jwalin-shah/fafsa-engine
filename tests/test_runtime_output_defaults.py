from __future__ import annotations

from pathlib import Path
import tomllib

from fafsa import isir


ROOT = Path(__file__).parents[1]


def _gitignore_patterns() -> set[str]:
    return {
        line.strip()
        for line in (ROOT / ".gitignore").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }


def test_pytest_cache_defaults_to_ignored_local_path():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())

    cache_dir = pyproject["tool"]["pytest"]["ini_options"]["cache_dir"]

    assert cache_dir == ".local/pytest-cache"
    assert ".local/" in _gitignore_patterns()


def test_runtime_output_paths_are_ignored():
    patterns = _gitignore_patterns()

    assert {
        ".local/",
        ".pytest_cache/",
        ".uv-cache/",
        ".tldr/",
        ".rtk/",
        "runs/",
        "outputs/",
        "artifacts/",
        "logs/",
        "*.log",
    } <= patterns


def test_validation_default_uses_tracked_fixture_not_output_path():
    fixture_path = isir._DEFAULT_ISIR_PATH.relative_to(ROOT)

    assert fixture_path == Path("data/IDSA25OP-20240308.txt")
    assert fixture_path.is_relative_to("data")
    assert not fixture_path.is_relative_to(".local")
    assert not fixture_path.is_relative_to("runs")
    assert not fixture_path.is_relative_to("outputs")
    assert (ROOT / "data" / "README.md").is_file()
