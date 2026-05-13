"""Real ED ground-truth validation.

These tests run the engine against the U.S. Department of Education's
published 2024-25 test ISIR file (data/IDSA25OP-20240308.txt). They keep the
local validation gate honest: the expected result must match the current
engine state, whether that state is green or red.
"""
from __future__ import annotations
from pathlib import Path

import pytest

from fafsa.isir import ISIRReport, _pi, compare_isir_intermediates, reconstruct_family, validate_isir_file
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
    assert report.passed == 22
    assert report.failed == 20
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
    assert first_failure["parent_input_source"] == "parent_fti"
    diagnostic_fields = {item["field"] for item in first_failure["diagnostics"]}
    assert "sai" in diagnostic_fields
    assert diagnostic_fields & {"paai", "pc", "sci", "eea", "sca"}


def test_report_summarizes_intermediate_diagnostics_for_red_gate(report):
    assert report.diagnostic_summary == {
        "sai": 20,
        "paai": 11,
        "pc": 11,
        "sci": 10,
    }


def test_report_summarizes_current_baseline_by_parent_input_source(report):
    assert report.source_summary == {
        "no_parent_fti": {"total": 7, "passed": 1, "failed": 6, "skipped": 0},
        "parent_fti": {"total": 35, "passed": 21, "failed": 14, "skipped": 0},
    }
    assert report.diagnostic_summary_by_source == {
        "no_parent_fti": {"paai": 6, "pc": 6, "sai": 6, "sci": 1},
        "parent_fti": {"sai": 14, "sci": 9, "paai": 5, "pc": 5},
    }


def test_report_summarizes_current_failure_signatures(report):
    assert report.failure_signature_summary == {
        "parent_fti:sci,sai": 9,
        "no_parent_fti:paai,pc,sai": 5,
        "parent_fti:paai,pc,sai": 5,
        "no_parent_fti:paai,pc,sci,sai": 1,
    }


def test_parent_asset_reconstruction_uses_isir_layout_positions():
    line = ISIR_FILE.read_text().splitlines()[87]
    family = reconstruct_family(line)
    trace = prove_sai(family)

    assert family.parent_cash_savings == 2500
    assert family.parent_investment_net_worth == 0
    assert family.parent_business_farm_net_worth == 0
    assert trace.sai == 1702
    assert trace.sai == _pi(line, "sai")


def test_parent_fti_reconstruction_uses_generated_parent_total_income():
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if _pi(line, "sai") == 2318 and _pi(line, "p_agi_fti") == 76589
    )
    family = reconstruct_family(line)
    trace = prove_sai(family)

    assert family.parent_agi == _pi(line, "parent_total_income")
    assert family.parent_earned_income_p1 == _pi(line, "p_agi_fti")
    assert family.parent_deductible_ira_payments == 0
    assert trace.sai == 2318
    assert trace.sai == _pi(line, "sai")


def test_no_parent_fti_reconstruction_uses_generated_parent_total_income(report):
    no_parent_fti_failures = [
        failure
        for failure in report.failures
        if failure["parent_input_source"] == "no_parent_fti"
    ]

    assert no_parent_fti_failures
    assert all(failure["p_agi"] > 0 for failure in no_parent_fti_failures)
    assert all(
        "eea" not in {item["field"] for item in failure["diagnostics"]}
        for failure in no_parent_fti_failures
    )


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
