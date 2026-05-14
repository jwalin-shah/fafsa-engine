"""Real ED ground-truth validation.

These tests run the engine against the U.S. Department of Education's
published 2024-25 test ISIR file (data/IDSA25OP-20240308.txt). They keep the
local validation gate honest: the expected result must match the current
engine state, whether that state is green or red.
"""
from __future__ import annotations
from pathlib import Path

import pytest

from fafsa.isir import (
    ISIRRecord,
    ISIRParseError,
    ISIRReport,
    _FIELDS,
    _pi,
    compare_isir_intermediates,
    reconstruct_family,
    validate_isir_file,
)
from fafsa.kb import prove_sai


ISIR_FILE = Path(__file__).parent.parent / "data" / "IDSA25OP-20240308.txt"


def _replace_field(line: str, key: str, value: str) -> str:
    start, end = _FIELDS[key]
    return line[:start] + value.ljust(end - start)[: end - start] + line[end:]


@pytest.fixture(scope="module")
def report() -> ISIRReport:
    if not ISIR_FILE.exists():
        pytest.skip(f"ISIR test file not present: {ISIR_FILE}")
    return validate_isir_file(ISIR_FILE)


def test_isir_file_has_dependent_records(report):
    assert report.total_file_lines > 0, "ISIR file is empty"
    assert report.dependent_records > 0, "No Formula A records found in ISIR file"
    assert report.total_file_lines > report.dependent_records


def test_engine_validation_matches_current_green_baseline(report):
    assert report.passed == 42
    assert report.failed == 0
    assert report.skipped == 0
    assert not report.failures


def test_isir_count_is_42(report):
    """ED's published file has exactly 42 Formula A (dependent) records.
    If this drops, either the file changed upstream or our parser broke."""
    assert report.dependent_records == 42


def test_report_distinguishes_file_lines_from_dependent_records(report):
    assert report.total_file_lines == 103
    assert report.dependent_records == report.passed + report.failed + report.skipped


def test_report_all_passed_property_is_true_when_gate_is_green(report):
    assert report.all_passed


def test_report_has_no_failure_diagnostics_when_gate_is_green(report):
    assert report.failures == []
    assert report.diagnostic_summary == {}
    assert report.diagnostic_summary_by_source == {}
    assert report.failure_signature_summary == {}


def test_isir_record_exposes_formula_a_validation_inputs():
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if ISIRRecord(line).is_dependent_formula_a
    )
    record = ISIRRecord(line, lineno=1)

    assert record.is_dependent_formula_a
    assert record.target_sai == _pi(line, "sai")
    assert record.parent_input_source in {"parent_fti", "no_parent_fti"}
    assert record.reconstruct_family().family_size > 0


def test_isir_validator_fails_when_expected_sai_is_corrupted(tmp_path):
    lines = ISIR_FILE.read_text().splitlines()
    dependent_index, line = next(
        (index, line) for index, line in enumerate(lines)
        if ISIRRecord(line).is_dependent_formula_a
    )
    lines[dependent_index] = _replace_field(line, "sai", str(_pi(line, "sai") + 1))
    corrupted_file = tmp_path / "corrupted-isir.txt"
    corrupted_file.write_text("\n".join(lines) + "\n")

    corrupted_report = validate_isir_file(corrupted_file)

    assert not corrupted_report.all_passed
    assert corrupted_report.passed == 41
    assert corrupted_report.failed == 1
    assert corrupted_report.skipped == 0
    assert corrupted_report.failures[0]["diagnostics"][-1]["field"] == "sai"


def test_isir_record_rejects_malformed_numeric_field():
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if ISIRRecord(line).is_dependent_formula_a
    )
    malformed_line = _replace_field(line, "p_earned_fti", "12X45")

    with pytest.raises(ISIRParseError) as excinfo:
        ISIRRecord(malformed_line, lineno=7).field_int("p_earned_fti")

    assert excinfo.value.key == "p_earned_fti"
    assert excinfo.value.value == "12X45"
    assert "line 7" in str(excinfo.value)
    assert "must be an integer or blank" in str(excinfo.value)


def test_isir_validator_rejects_malformed_numeric_input(tmp_path):
    lines = ISIR_FILE.read_text().splitlines()
    dependent_index, line = next(
        (index, line) for index, line in enumerate(lines)
        if ISIRRecord(line).is_dependent_formula_a
    )
    lines[dependent_index] = _replace_field(line, "p_earned_fti", "12X45")
    malformed_file = tmp_path / "malformed-isir.txt"
    malformed_file.write_text("\n".join(lines) + "\n")

    malformed_report = validate_isir_file(malformed_file)

    assert not malformed_report.all_passed
    assert malformed_report.passed == 41
    assert malformed_report.failed == 1
    assert malformed_report.skipped == 0
    assert malformed_report.source_summary["parse_error"] == {
        "total": 1,
        "passed": 0,
        "failed": 1,
        "skipped": 0,
    }
    assert malformed_report.failures[0]["field"] == "p_earned_fti"
    assert malformed_report.failures[0]["raw_value"] == "12X45"
    assert "must be an integer or blank" in malformed_report.failures[0]["error"]


def test_report_summarizes_current_baseline_by_parent_input_source(report):
    assert report.source_summary == {
        "no_parent_fti": {"total": 6, "passed": 6, "failed": 0, "skipped": 0},
        "parent_fti": {"total": 36, "passed": 36, "failed": 0, "skipped": 0},
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


def test_parent_fti_source_rule_is_shared_by_classification_and_reconstruction():
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if ISIRRecord(line).is_dependent_formula_a
    )
    for key in (
        "p_agi_fti",
        "p_tax_fti",
        "p_ira_fti",
        "p_spouse_earned_fti",
        "p_spouse_tax_fti",
        "p_filing_status_fti",
    ):
        line = _replace_field(line, key, "")
    line = _replace_field(line, "p_earned_fti", "12345")
    line = _replace_field(line, "p_manual_filing_status", "3")

    record = ISIRRecord(line)
    family = record.reconstruct_family()

    assert record.has_parent_fti_income_or_tax_source
    assert record.parent_input_source == "parent_fti"
    assert family.parent_earned_income_p1 == 12345
    assert family.parent_filing_status == 0


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


def test_parent_fti_self_reported_spouse_fields_override_spouse_fti_values():
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if _pi(line, "sai") == -921 and _pi(line, "p_spouse_manual_earned_income") == 8456
    )
    family = reconstruct_family(line)
    trace = prove_sai(family)
    trace_values = {step.label: int(step.value) for step in trace.steps}

    assert _pi(line, "p_spouse_earned_fti") == 25000
    assert _pi(line, "p_spouse_tax_fti") == 9568
    assert _pi(line, "p_spouse_manual_earned_income") == 8456
    assert _pi(line, "p_spouse_manual_tax") == 102
    assert family.parent_income_tax_paid == 14589 + 102
    assert family.parent_earned_income_p1 == 49568
    assert family.parent_earned_income_p2 == 8456
    assert trace_values["parent_payroll_tax"] == _pi(line, "parent_payroll_tax")
    assert trace_values["parent_total_allowances"] == _pi(line, "parent_total_allowances")
    assert trace_values["parent_available_income"] == _pi(line, "parent_available_income")
    assert trace_values["parent_adjusted_available_income"] == _pi(line, "paai")
    assert trace_values["parent_contribution"] == _pi(line, "pc")
    assert trace.sai == -921
    assert trace.sai == _pi(line, "sai")


def test_public_validation_fails_without_parent_spouse_self_reported_override(tmp_path):
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if _pi(line, "sai") == -921 and _pi(line, "p_spouse_manual_earned_income") == 8456
    )
    single_record_file = tmp_path / "single-isir.txt"
    single_record_file.write_text(line + "\n")

    original_report = validate_isir_file(single_record_file)

    assert original_report.all_passed
    assert original_report.passed == 1

    mutated_line = _replace_field(line, "p_spouse_manual_earned_income", "")
    mutated_line = _replace_field(mutated_line, "p_spouse_manual_tax", "")
    mutated_file = tmp_path / "missing-spouse-manual-override-isir.txt"
    mutated_file.write_text(mutated_line + "\n")

    mutated_report = validate_isir_file(mutated_file)

    assert not mutated_report.all_passed
    assert mutated_report.passed == 0
    assert mutated_report.failed == 1
    assert mutated_report.failures[0]["target"] == -921
    assert mutated_report.failures[0]["actual"] == -1500
    assert mutated_report.failures[0]["parent_input_source"] == "parent_fti"
    assert mutated_report.failures[0]["parent_earned_income_p2"] == 25000
    assert mutated_report.failures[0]["p_tax"] == 24157
    assert mutated_report.diagnostic_summary["sai"] == 1
    assert mutated_report.diagnostic_summary["parent_payroll_tax"] == 1


def test_parent_self_reported_agi_overrides_parent_fti_agi_without_total_income_proxy():
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if _pi(line, "sai") == -921 and _pi(line, "p_agi_fti") == 53025
    )
    line = _replace_field(line, "parent_total_income", "")
    line = _replace_field(line, "p_manual_agi", "61000")
    line = _replace_field(line, "p_spouse_manual_agi", "9000")

    family = reconstruct_family(line)

    assert _pi(line, "p_agi_fti") == 53025
    assert _pi(line, "p_spouse_agi_fti") == 25689
    assert family.parent_agi == 70000


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


def test_self_reported_zero_does_not_replace_populated_parent_spouse_fti_field():
    line = next(
        line for line in ISIR_FILE.read_text().splitlines()
        if _pi(line, "sai") == -921 and _pi(line, "p_spouse_tax_fti") == 9568
    )
    line_with_zero_manual_tax = _replace_field(line, "p_spouse_manual_tax", "0")

    family = reconstruct_family(line_with_zero_manual_tax)

    assert _pi(line_with_zero_manual_tax, "p_spouse_manual_tax") == 0
    assert family.parent_income_tax_paid == _pi(line, "p_tax_fti") + _pi(line, "p_spouse_tax_fti")


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
    record = ISIRRecord(line)
    if not record.is_dependent_formula_a:
        return []
    return record.compare_intermediates(prove_sai(record.reconstruct_family()))
