"""Real ED ground-truth validation.

These tests run the engine against the U.S. Department of Education's
published 2024-25 test ISIR file (data/IDSA25OP-20240308.txt). They keep the
local validation gate honest: the expected result must match the current
engine state, whether that state is green or red.
"""
from __future__ import annotations
from pathlib import Path

import pytest

from fafsa.isir import ISIRReport, compare_isir_intermediates, reconstruct_family, validate_isir_file
from fafsa.kb import prove_sai


ISIR_FILE = Path(__file__).parent.parent / "data" / "IDSA25OP-20240308.txt"


@pytest.fixture(scope="module")
def report() -> ISIRReport:
    if not ISIR_FILE.exists():
        pytest.skip(f"ISIR test file not present: {ISIR_FILE}")
    return validate_isir_file(ISIR_FILE)


def test_isir_file_has_dependent_records(report):
    assert report.total_file_lines > 0, "ISIR file is empty"
    assert report.dependent_records > 0, "No Formula A records found in ISIR file"
    assert report.total_file_lines > report.dependent_records


def test_engine_validation_matches_current_red_baseline(report):
    assert report.passed == 2
    assert report.failed == 40
    assert report.skipped == 0
    assert report.failures, "Expected current engine to disagree with ED records"


def test_isir_count_is_42(report):
    """ED's published file has exactly 42 Formula A (dependent) records.
    If this drops, either the file changed upstream or our parser broke."""
    assert report.dependent_records == 42


def test_report_distinguishes_file_lines_from_dependent_records(report):
    assert report.total_file_lines == 103
    assert report.dependent_records == report.passed + report.failed + report.skipped


def test_report_all_passed_property_is_false_when_gate_is_red(report):
    assert not report.all_passed


def test_failures_include_intermediate_diagnostics(report):
    first_failure = report.failures[0]

    assert first_failure["diagnostics"], "Expected failing records to include field-level diagnostics"
    diagnostic_fields = {item["field"] for item in first_failure["diagnostics"]}
    assert "sai" in diagnostic_fields
    assert diagnostic_fields & {"paai", "pc", "sci", "eea", "sca"}


def test_intermediate_comparison_names_expected_isir_fields():
    line = next(line for line in ISIR_FILE.read_text().splitlines() if _diagnostics_for_line(line))
    trace = prove_sai(reconstruct_family(line))

    diagnostics = compare_isir_intermediates(line, trace)

    assert diagnostics
    assert {item["field"] for item in diagnostics} <= {"ipa", "eea", "paai", "pc", "sci", "sca", "sai"}
    assert all({"field", "trace_label", "expected", "actual", "delta"} <= set(item) for item in diagnostics)


def _diagnostics_for_line(line: str):
    if len(line) < 7700 or line[187:188] != "A":
        return []
    return compare_isir_intermediates(line, prove_sai(reconstruct_family(line)))
