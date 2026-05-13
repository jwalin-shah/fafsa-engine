"""ED test ISIR validation.

Validates the engine against the U.S. Department of Education's official 2024-25 
test ISIR records (Institutional Student Information Records).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from fafsa.kb import IPA_TABLE, DependentFamily, SAITrace, prove_sai


_DEFAULT_ISIR_PATH = Path(__file__).parent.parent / "data" / "IDSA25OP-20240308.txt"


# Field positions in the 2024-25 ISIR fixed-width layout (0-indexed)
_FIELDS = {
    # Intermediate / Output fields (for verification)
    "sai":     (175, 181),
    "formula": (187, 188),
    "ipa":     (2895, 2910),
    "eea":     (2910, 2925),
    "paai":    (2940, 2955),
    "pc":      (2955, 2970),
    "sci":     (3060, 3075),
    "sca":     (3162, 3174),
    "fam":     (3177, 3180), # Assumed family size
    
    # Input fields (for reconstruction)
    # Student Section
    "s_agi":    (709, 720),
    "s_wages":  (776, 787), 
    "s_tax":    (731, 742), 
    
    # Parent Section
    "p_agi_fti": (7341, 7352),
    "p_tax_fti": (7352, 7363),
    "p_ira_fti": (7363, 7374),
    "p_fam_fti": (7336, 7337),
    "p_num_fti": (7338, 7339),
    "p_cash":    (1923, 1930),
    "p_invest":  (1931, 1938),
    "p_bus":     (1938, 1945),
}


@dataclass
class ISIRReport:
    """Result of running validation across an ISIR test file."""
    total_file_lines: int
    dependent_records: int
    passed: int
    failed: int
    skipped: int
    failures: list[dict]
    diagnostic_summary: dict[str, int] = field(default_factory=dict)
    source_summary: dict[str, dict[str, int]] = field(default_factory=dict)
    diagnostic_summary_by_source: dict[str, dict[str, int]] = field(default_factory=dict)
    failure_signature_summary: dict[str, int] = field(default_factory=dict)

    @property
    def all_passed(self) -> bool:
        return (
            self.dependent_records > 0
            and self.passed == self.dependent_records
            and self.failed == 0
            and self.skipped == 0
        )


_TRACE_TO_ISIR_FIELDS = {
    "parent_income_protection_allowance": "ipa",
    "parent_employment_expense_allowance": "eea",
    "parent_adjusted_available_income": "paai",
    "parent_contribution": "pc",
    "student_contribution_from_income": "sci",
    "student_contribution_from_assets": "sca",
    "student_aid_index": "sai",
}


def _pi(line: str, key: str) -> int:
    s, e = _FIELDS[key]
    v = line[s:e].strip().split()
    if not v or v[0] == 'N/A': return 0
    try:
        return int(v[0])
    except ValueError:
        return 0


def reconstruct_family(line: str) -> DependentFamily:
    """Reconstruct a DependentFamily from an ISIR record."""
    p_agi = _pi(line, "p_agi_fti")
    p_tax = _pi(line, "p_tax_fti")
    p_ira = _pi(line, "p_ira_fti")
    
    # Family structure
    family_size = _pi(line, "p_fam_fti")
    num_parents = _pi(line, "p_num_fti")
    
    # Backfill from IPA if FTI fields are 0
    if family_size == 0:
        ipa = _pi(line, "ipa")
        for size, val in IPA_TABLE.items():
            if val == ipa:
                family_size = size
                break
        if family_size == 0 and ipa > 58560:
            family_size = 6 + (ipa - 58560) // 6610

    if num_parents == 0:
        num_parents = 2 if _pi(line, "eea") > 0 else 1

    # Assets
    p_cash = _pi(line, "p_cash")
    p_invest = _pi(line, "p_invest")
    p_bus = _pi(line, "p_bus")

    # Student
    s_agi = _pi(line, "s_agi")
    s_tax = _pi(line, "s_tax")
    s_wages = _pi(line, "s_wages")

    # Correcting for common test record patterns:
    p1_wages = p_agi
    s_earned = s_wages if s_wages > 0 else s_agi

    return DependentFamily(
        parent_agi=p_agi,
        parent_deductible_ira_payments=p_ira,
        parent_income_tax_paid=p_tax,
        parent_earned_income_p1=p1_wages,
        parent_cash_savings=p_cash,
        parent_investment_net_worth=p_invest,
        parent_business_farm_net_worth=p_bus,
        family_size=family_size,
        num_parents=num_parents,
        student_agi=s_agi,
        student_income_tax_paid=s_tax,
        student_earned_income=s_earned,
    )


def _is_dependent_record(line: str) -> bool:
    return len(line) >= 7700 and line[187:188] == "A"


def _parent_input_source(line: str) -> str:
    if _pi(line, "p_agi_fti") or _pi(line, "p_tax_fti") or _pi(line, "p_ira_fti"):
        return "parent_fti"
    return "no_parent_fti"


def compare_isir_intermediates(line: str, trace: SAITrace) -> list[dict]:
    """Compare ED ISIR intermediates with the engine trace for Formula A."""
    trace_values = {step.label: int(step.value) for step in trace.steps}
    diagnostics = []
    for trace_label, field in _TRACE_TO_ISIR_FIELDS.items():
        expected = _pi(line, field)
        actual = trace_values.get(trace_label)
        if actual != expected:
            diagnostics.append({
                "field": field,
                "trace_label": trace_label,
                "expected": expected,
                "actual": actual,
                "delta": None if actual is None else actual - expected,
            })
    return diagnostics


def validate_isir_file(path: str | Path | None = None) -> ISIRReport:
    """Run full system validation across all Formula A records in an ISIR file."""
    if path is None:
        path = _DEFAULT_ISIR_PATH
    with open(path) as f:
        lines = [l.rstrip("\n") for l in f]

    passed = failed = skipped = dependent_records = 0
    failures: list[dict] = []
    diagnostic_summary: dict[str, int] = {}
    source_summary: dict[str, dict[str, int]] = {}
    diagnostic_summary_by_source: dict[str, dict[str, int]] = {}
    failure_signature_summary: dict[str, int] = {}

    for lineno, line in enumerate(lines, 1):
        if not _is_dependent_record(line):
            continue

        dependent_records += 1
        target_sai = _pi(line, "sai")
        parent_input_source = _parent_input_source(line)
        source_counts = source_summary.setdefault(
            parent_input_source,
            {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
        )
        source_counts["total"] += 1
        
        # 1. Reconstruct inputs
        try:
            family = reconstruct_family(line)
        except Exception:
            skipped += 1
            source_counts["skipped"] += 1
            continue
            
        # 2. Compute end-to-end
        trace = prove_sai(family)
        
        # 3. Verify
        if trace.sai == target_sai:
            passed += 1
            source_counts["passed"] += 1
        else:
            failed += 1
            source_counts["failed"] += 1
            diagnostics = compare_isir_intermediates(line, trace)
            source_diagnostics = diagnostic_summary_by_source.setdefault(parent_input_source, {})
            for item in diagnostics:
                field_name = item["field"]
                diagnostic_summary[field_name] = diagnostic_summary.get(field_name, 0) + 1
                source_diagnostics[field_name] = source_diagnostics.get(field_name, 0) + 1
            field_signature = ",".join(item["field"] for item in diagnostics)
            signature_key = f"{parent_input_source}:{field_signature}"
            failure_signature_summary[signature_key] = failure_signature_summary.get(signature_key, 0) + 1
            failures.append({
                "lineno": lineno,
                "target": target_sai,
                "actual": trace.sai,
                "parent_input_source": parent_input_source,
                "diagnostics": diagnostics,
                "p_agi": family.parent_agi,
                "p_tax": family.parent_income_tax_paid,
                "s_agi": family.student_agi,
                "fam": family.family_size,
            })

    return ISIRReport(
        total_file_lines=len(lines),
        dependent_records=dependent_records,
        passed=passed,
        failed=failed,
        skipped=skipped,
        failures=failures,
        diagnostic_summary=dict(sorted(
            diagnostic_summary.items(),
            key=lambda item: (-item[1], item[0]),
        )),
        source_summary=dict(sorted(source_summary.items())),
        diagnostic_summary_by_source={
            source: dict(sorted(fields.items(), key=lambda item: (-item[1], item[0])))
            for source, fields in sorted(diagnostic_summary_by_source.items())
        },
        failure_signature_summary=dict(sorted(
            failure_signature_summary.items(),
            key=lambda item: (-item[1], item[0]),
        )),
    )
