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
    assert report.passed == 34
    assert report.failed == 8
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
        "sai": 8,
        "paai": 7,
        "parent_total_allowances": 7,
        "pc": 7,
        "sci": 1,
        "student_available_income": 1,
        "student_total_allowances": 1,
    }


def test_report_summarizes_current_baseline_by_parent_input_source(report):
    assert report.source_summary == {
        "no_parent_fti": {"total": 6, "passed": 1, "failed": 5, "skipped": 0},
        "parent_fti": {"total": 36, "passed": 33, "failed": 3, "skipped": 0},
    }
    assert report.diagnostic_summary_by_source == {
        "no_parent_fti": {
            "paai": 5,
            "parent_total_allowances": 5,
            "pc": 5,
            "sai": 5,
        },
        "parent_fti": {
            "sai": 3,
            "paai": 2,
            "parent_total_allowances": 2,
            "pc": 2,
            "sci": 1,
            "student_available_income": 1,
            "student_total_allowances": 1,
        },
    }


def test_report_summarizes_current_failure_signatures(report):
    assert report.failure_signature_summary == {
        "no_parent_fti:parent_total_allowances,paai,pc,sai": 5,
        "parent_fti:parent_total_allowances,paai,pc,sai": 1,
        "parent_fti:parent_total_allowances,paai,pc,student_total_allowances,student_available_income,sai": 1,
        "parent_fti:sci,sai": 1,
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


def test_parent_child_support_reconstruction_uses_isir_layout_position():
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if _pi(line, "sai") == 46607 and _pi(line, "parent_total_income") == 158360
    )
    family = reconstruct_family(line)
    trace = prove_sai(family)
    trace_values = {step.label: int(step.value) for step in trace.steps}

    assert family.parent_child_support_received == 30000
    assert family.parent_cash_savings == 26500
    assert trace_values["parent_net_worth"] == 56500


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


def test_parent_fti_reconstruction_includes_spouse_earnings_and_tax():
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if _pi(line, "sai") == 4514 and _pi(line, "parent_total_income") == 88021
    )
    family = reconstruct_family(line)
    trace = prove_sai(family)
    trace_values = {step.label: int(step.value) for step in trace.steps}

    assert family.parent_income_tax_paid == _pi(line, "p_tax_fti") + _pi(line, "p_spouse_tax_fti")
    assert family.parent_earned_income_p1 == _pi(line, "p_agi_fti")
    assert family.parent_earned_income_p2 == _pi(line, "p_spouse_earned_fti")
    assert trace_values["parent_total_allowances"] == _pi(line, "parent_total_allowances")
    assert trace.sai == 4514
    assert trace.sai == _pi(line, "sai")


def test_parent_fti_spouse_only_earnings_do_not_backfill_parent_wages():
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if _pi(line, "sai") == -61 and _pi(line, "p_spouse_earned_fti") == 51068
    )
    family = reconstruct_family(line)
    trace = prove_sai(family)
    trace_values = {step.label: int(step.value) for step in trace.steps}

    assert not _pi(line, "p_agi_fti")
    assert family.parent_agi == _pi(line, "parent_total_income")
    assert family.parent_earned_income_p1 == 0
    assert family.parent_earned_income_p2 == _pi(line, "p_spouse_earned_fti")
    assert trace_values["parent_payroll_tax"] == _pi(line, "parent_payroll_tax")
    assert trace.sai == -61
    assert trace.sai == _pi(line, "sai")


def test_student_reconstruction_uses_corrected_isir_offsets():
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if _pi(line, "sai") == 6096 and _pi(line, "p_agi_fti") == 75000
    )
    family = reconstruct_family(line)
    trace = prove_sai(family)

    assert _pi(line, "student_total_income") == 3512
    assert not _pi(line, "s_agi_fti")
    assert family.student_agi == _pi(line, "student_total_income")
    assert family.student_earned_income == _pi(line, "s_wages")
    assert trace.sai == 6096
    assert trace.sai == _pi(line, "sai")


def test_student_fti_reconstruction_uses_tax_and_earned_income_fields():
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if _pi(line, "sai") == -587 and _pi(line, "student_total_income") == 11056
    )
    family = reconstruct_family(line)
    trace = prove_sai(family)
    trace_values = {step.label: int(step.value) for step in trace.steps}

    assert family.student_agi == _pi(line, "s_agi_fti")
    assert family.student_income_tax_paid == _pi(line, "s_tax_fti")
    assert family.student_earned_income == _pi(line, "s_earned_fti")
    assert trace_values["student_total_allowances"] == _pi(line, "student_total_allowances")
    assert trace.sai == -587
    assert trace.sai == _pi(line, "sai")


def test_student_source_adjustments_reconstruct_formula_a_total_income():
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if _pi(line, "sai") == 6685 and _pi(line, "s_agi_fti") == 10456
    )
    family = reconstruct_family(line)
    trace = prove_sai(family)
    trace_values = {step.label: int(step.value) for step in trace.steps}

    assert family.student_taxable_scholarships == 5000
    assert family.student_foreign_income_exclusion == 10225
    assert family.student_work_study == 1000
    assert trace_values["student_total_income"] == _pi(line, "student_total_income")
    assert trace.sai == 6685
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
    assert {item["field"] for item in diagnostics} <= {
        "ipa",
        "eea",
        "parent_total_allowances",
        "paai",
        "pc",
        "student_total_income",
        "student_total_allowances",
        "student_available_income",
        "sci",
        "sca",
        "sai",
    }
    assert all({"field", "trace_label", "expected", "actual", "delta"} <= set(item) for item in diagnostics)


def _diagnostics_for_line(line: str):
    if len(line) < 7700 or line[187:188] != "A":
        return []
    return compare_isir_intermediates(line, prove_sai(reconstruct_family(line)))
