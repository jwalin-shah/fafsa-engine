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
    assert report.passed == 41
    assert report.failed == 1
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
    assert diagnostic_fields & {"paai", "pc", "eea", "sca"}


def test_report_summarizes_intermediate_diagnostics_for_red_gate(report):
    assert report.diagnostic_summary == {
        "sai": 1,
        "parent_available_income": 1,
        "parent_payroll_tax": 1,
        "paai": 1,
        "parent_total_allowances": 1,
        "pc": 1,
        "parents_negative_paai_allowance": 1,
        "student_available_income": 1,
        "student_total_allowances": 1,
    }


def test_report_summarizes_current_baseline_by_parent_input_source(report):
    assert report.source_summary == {
        "no_parent_fti": {"total": 6, "passed": 6, "failed": 0, "skipped": 0},
        "parent_fti": {"total": 36, "passed": 35, "failed": 1, "skipped": 0},
    }
    assert report.diagnostic_summary_by_source == {
        "parent_fti": {
            "sai": 1,
            "paai": 1,
            "parent_available_income": 1,
            "parent_payroll_tax": 1,
            "parent_total_allowances": 1,
            "parents_negative_paai_allowance": 1,
            "pc": 1,
            "student_available_income": 1,
            "student_total_allowances": 1,
        },
    }


def test_report_summarizes_current_failure_signatures(report):
    assert report.failure_signature_summary == {
        "parent_fti:parent_payroll_tax,parent_total_allowances,parent_available_income,paai,pc,parents_negative_paai_allowance,student_total_allowances,student_available_income,sai": 1,
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
        if _pi(line, "sai") == 2318 and _pi(line, "p_earned_fti") == 76589
    )
    family = reconstruct_family(line)
    trace = prove_sai(family)

    assert family.parent_agi == _pi(line, "parent_total_income")
    assert _pi(line, "p_agi_fti") == 78125
    assert family.parent_earned_income_p1 == _pi(line, "p_earned_fti")
    assert family.parent_deductible_ira_payments == 0
    assert trace.sai == 2318
    assert trace.sai == _pi(line, "sai")


def test_parent_fti_layout_distinguishes_agi_from_earned_income():
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if _pi(line, "sai") == 2318 and _pi(line, "p_earned_fti") == 76589
    )
    family = reconstruct_family(line)

    assert _pi(line, "p_agi_fti") == 78125
    assert _pi(line, "p_earned_fti") == 76589
    assert family.parent_agi == _pi(line, "parent_total_income")
    assert family.parent_earned_income_p1 == _pi(line, "p_earned_fti")


def test_parent_fti_reconstruction_includes_spouse_earnings_and_tax():
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if _pi(line, "sai") == 4514 and _pi(line, "parent_total_income") == 88021
    )
    family = reconstruct_family(line)
    trace = prove_sai(family)
    trace_values = {step.label: int(step.value) for step in trace.steps}

    assert family.parent_income_tax_paid == _pi(line, "p_tax_fti") + _pi(line, "p_spouse_tax_fti")
    assert family.parent_earned_income_p1 == _pi(line, "p_earned_fti")
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


def test_parent_fti_filing_status_controls_payroll_jointness():
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if _pi(line, "sai") == 28409 and _pi(line, "p_earned_fti") == 155895
    )
    family = reconstruct_family(line)
    trace = prove_sai(family)
    trace_values = {step.label: int(step.value) for step in trace.steps}

    assert family.num_parents == 2
    assert family.parent_filing_status == 4
    assert trace_values["parent_payroll_tax"] == _pi(line, "parent_payroll_tax")
    assert trace.sai == 28409
    assert trace.sai == _pi(line, "sai")


def test_remaining_parent_fti_failure_exposes_negative_paai_allowance_drift(report):
    failure = next(
        failure
        for failure in report.failures
        if failure["parent_input_source"] == "parent_fti"
    )
    diagnostics = {item["field"]: item for item in failure["diagnostics"]}

    assert failure["target"] == -921
    assert diagnostics["parent_available_income"]["delta"] == -10732
    assert diagnostics["parents_negative_paai_allowance"]["expected"] == 0
    assert diagnostics["parents_negative_paai_allowance"]["actual"] == 8100
    assert (
        diagnostics["student_total_allowances"]["delta"]
        == diagnostics["parents_negative_paai_allowance"]["delta"]
    )


def test_student_reconstruction_uses_corrected_isir_offsets():
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if _pi(line, "sai") == 6096 and _pi(line, "p_earned_fti") == 75000
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


def test_no_parent_fti_reconstruction_uses_manual_parent_source_fields():
    lines = ISIR_FILE.read_text().splitlines()

    cases = [
        {
            "sai": 8292,
            "manual_status": 3,
            "manual_agi": 95078,
            "spouse_agi": 0,
            "manual_wages": 94999,
            "spouse_wages": 0,
            "manual_tax": 10042,
            "spouse_tax": 0,
        },
        {
            "sai": 1702,
            "manual_status": 1,
            "manual_agi": 42000,
            "spouse_agi": 19000,
            "manual_wages": 42000,
            "spouse_wages": 19000,
            "manual_tax": 2000,
            "spouse_tax": 1000,
        },
        {
            "sai": 46607,
            "manual_status": 3,
            "manual_agi": 158360,
            "spouse_agi": 0,
            "manual_wages": 158000,
            "spouse_wages": 0,
            "manual_tax": 27996,
            "spouse_tax": 0,
        },
    ]

    for case in cases:
        line = next(line for line in lines if _pi(line, "sai") == case["sai"])
        family = reconstruct_family(line)
        trace = prove_sai(family)
        trace_values = {step.label: int(step.value) for step in trace.steps}

        assert _pi(line, "p_manual_filing_status") == case["manual_status"]
        assert _pi(line, "p_manual_agi") == case["manual_agi"]
        assert _pi(line, "p_spouse_manual_agi") == case["spouse_agi"]
        assert _pi(line, "p_manual_earned_income") == case["manual_wages"]
        assert _pi(line, "p_spouse_manual_earned_income") == case["spouse_wages"]
        assert _pi(line, "p_manual_tax") == case["manual_tax"]
        assert _pi(line, "p_spouse_manual_tax") == case["spouse_tax"]
        assert family.parent_agi == _pi(line, "parent_total_income")
        assert family.parent_filing_status == case["manual_status"]
        assert family.parent_earned_income_p1 == case["manual_wages"]
        assert family.parent_earned_income_p2 == case["spouse_wages"]
        assert family.parent_income_tax_paid == case["manual_tax"] + case["spouse_tax"]
        assert trace_values["parent_payroll_tax"] == _pi(line, "parent_payroll_tax")
        assert trace.sai == case["sai"]


def test_no_parent_fti_records_now_pass_without_failure_diagnostics(report):
    assert report.source_summary["no_parent_fti"] == {
        "total": 6,
        "passed": 6,
        "failed": 0,
        "skipped": 0,
    }
    assert all(failure["parent_input_source"] != "no_parent_fti" for failure in report.failures)


def test_intermediate_comparison_names_expected_isir_fields():
    line = next(line for line in ISIR_FILE.read_text().splitlines() if _diagnostics_for_line(line))
    trace = prove_sai(reconstruct_family(line))

    diagnostics = compare_isir_intermediates(line, trace)

    assert diagnostics
    assert {item["field"] for item in diagnostics} <= {
        "ipa",
        "eea",
        "parent_payroll_tax",
        "parent_total_allowances",
        "parent_available_income",
        "paai",
        "pc",
        "parents_negative_paai_allowance",
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
