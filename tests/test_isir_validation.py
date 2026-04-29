"""Real ED ground-truth validation.

These tests run the engine against the U.S. Department of Education's
published 2024-25 test ISIR file (data/IDSA25OP-20240308.txt). They verify
that the engine's components — the parent contribution schedule, SAI
summation arithmetic, and IPA table — agree with ED's own test data.

If any of these tests fail, the engine has diverged from federal ground
truth and any SAI it produces should not be trusted.
"""
from __future__ import annotations
from pathlib import Path

import pytest

from fafsa.isir import validate_isir_file, ISIRReport


ISIR_FILE = Path(__file__).parent.parent / "data" / "IDSA25OP-20240308.txt"


@pytest.fixture(scope="module")
def report() -> ISIRReport:
    if not ISIR_FILE.exists():
        pytest.skip(f"ISIR test file not present: {ISIR_FILE}")
    return validate_isir_file(ISIR_FILE)


def test_isir_file_has_dependent_records(report):
    assert report.total > 0, "No Formula A records found in ISIR file"


def test_engine_passes_all_isir_records(report):
    assert report.failed == 0, f"Engine disagrees with ED on: {report.failures[:3]}"


def test_isir_count_is_42(report):
    """ED's published file has exactly 42 Formula A (dependent) records.
    If this drops, either the file changed upstream or our parser broke."""
    assert report.passed == 42
    assert report.skipped == 0


def test_report_all_passed_property(report):
    assert report.all_passed
