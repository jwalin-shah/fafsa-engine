import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_demo_smoke_runs_without_llm_or_secrets():
    result = subprocess.run(
        [sys.executable, "demo.py", "--smoke"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "FAFSA CLI smoke: ok" in result.stdout
    assert "engine validated" in result.stdout
    assert result.stderr == ""


def test_demo_missing_query_fails_clearly():
    result = subprocess.run(
        [sys.executable, "demo.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "query is required unless --smoke is used" in result.stderr
    assert "usage:" in result.stderr
