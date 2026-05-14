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
    "parent_available_income": (2925, 2940),
    "paai":    (2940, 2955),
    "pc":      (2955, 2970),
    "parents_negative_paai_allowance": (3000, 3015),
    "sci":     (3060, 3075),
    "sca":     (3162, 3174),
    "fam":     (3177, 3180), # Assumed family size
    "student_total_allowances": (3030, 3045),
    "student_available_income": (3045, 3060),
    "student_total_income": (7609, 7624),
    "parent_total_allowances": (2865, 2880),
    "parent_payroll_tax":      (2880, 2895),
    "parent_total_income":     (7624, 7639),
    
    # Input fields (for reconstruction)
    # Student Section
    "s_wages":  (710, 721),
    "s_agi":    (776, 786),
    "s_tax":    (786, 795),
    "s_taxable_scholarships": (829, 836),
    "s_foreign_income_exclusion": (836, 846),
    "s_work_study": (2817, 2829),
    "s_agi_fti": (7101, 7111),
    "s_earned_fti": (7115, 7126),
    "s_tax_fti": (7126, 7135),
    
    # Parent Section
    "p_manual_filing_status": (1801, 1802),
    "p_manual_earned_income": (1802, 1813),
    "p_manual_agi": (1868, 1878),
    "p_manual_tax": (1878, 1887),
    "p_spouse_manual_earned_income": (2294, 2305),
    "p_spouse_manual_agi": (2360, 2370),
    "p_spouse_manual_tax": (2370, 2379),
    "p_filing_status_fti": (7326, 7327),
    "p_agi_fti": (7327, 7337),
    "p_num_exemptions_fti": (7337, 7339),
    "p_num_dependents_fti": (7339, 7341),
    "p_earned_fti": (7341, 7352),
    "p_tax_fti": (7352, 7361),
    "p_education_credits_fti": (7361, 7370),
    "p_untaxed_ira_distributions_fti": (7370, 7381),
    "p_ira_fti": (7381, 7392),
    "p_spouse_filing_status_fti": (7439, 7440),
    "p_spouse_agi_fti": (7440, 7450),
    "p_spouse_earned_fti": (7454, 7465),
    "p_spouse_tax_fti": (7465, 7474),
    "p_spouse_education_credits_fti": (7474, 7483),
    "p_spouse_untaxed_ira_distributions_fti": (7483, 7494),
    "p_fam_fti": (7336, 7337),
    "p_num_fti": (7338, 7339),
    "p_cash":    (1945, 1952),
    "p_invest":  (1952, 1959),
    "p_bus":     (1959, 1966),
    "p_child_support": (1938, 1945),
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
    "parent_payroll_tax": "parent_payroll_tax",
    "parent_total_allowances": "parent_total_allowances",
    "parent_available_income": "parent_available_income",
    "parent_adjusted_available_income": "paai",
    "parent_contribution": "pc",
    "parents_negative_paai_allowance": "parents_negative_paai_allowance",
    "student_total_income": "student_total_income",
    "student_total_allowances": "student_total_allowances",
    "student_available_income": "student_available_income",
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


def _has_value(line: str, key: str) -> bool:
    s, e = _FIELDS[key]
    v = line[s:e].strip().split()
    return bool(v and v[0] != "N/A")


def _has_manual_override(line: str, key: str) -> bool:
    return _has_value(line, key) and _pi(line, key) != 0


def reconstruct_family(line: str) -> DependentFamily:
    """Reconstruct a DependentFamily from an ISIR record."""
    p_agi = _pi(line, "p_agi_fti")
    p_tax = _pi(line, "p_tax_fti")
    p_ira = _pi(line, "p_ira_fti")
    p_filing_status = _pi(line, "p_filing_status_fti")
    p_manual_filing_status = _pi(line, "p_manual_filing_status")
    p_manual_earned_income = _pi(line, "p_manual_earned_income")
    p_manual_agi = _pi(line, "p_manual_agi")
    p_manual_tax = _pi(line, "p_manual_tax")
    p_spouse_manual_earned_income = _pi(line, "p_spouse_manual_earned_income")
    p_spouse_manual_agi = _pi(line, "p_spouse_manual_agi")
    p_spouse_manual_tax = _pi(line, "p_spouse_manual_tax")
    p_earned_income = _pi(line, "p_earned_fti")
    p_spouse_earned_income = _pi(line, "p_spouse_earned_fti")
    p_spouse_tax = _pi(line, "p_spouse_tax_fti")
    parent_fti_missing = (
        p_agi == 0
        and p_tax == 0
        and p_ira == 0
        and p_spouse_earned_income == 0
        and p_spouse_tax == 0
    )

    if _has_manual_override(line, "p_manual_agi") or _has_manual_override(line, "p_spouse_manual_agi"):
        p_agi = (
            p_manual_agi if _has_manual_override(line, "p_manual_agi") else p_agi
        ) + (
            p_spouse_manual_agi if _has_manual_override(line, "p_spouse_manual_agi") else 0
        )
    if _has_manual_override(line, "p_manual_tax"):
        p_tax = p_manual_tax
    if _has_manual_override(line, "p_spouse_manual_tax"):
        p_spouse_tax = p_spouse_manual_tax
    if _has_manual_override(line, "p_manual_earned_income"):
        p_earned_income = p_manual_earned_income
    if _has_manual_override(line, "p_spouse_manual_earned_income"):
        p_spouse_earned_income = p_spouse_manual_earned_income
    p_tax += p_spouse_tax

    p_total_income = _pi(line, "parent_total_income")
    if p_total_income:
        p_agi = p_total_income
        # The generated parent total income is already Formula A line 3, so
        # income additions such as deductible IRA payments must not be added
        # again by the core formula engine.
        p_ira = 0

    if parent_fti_missing:
        if p_manual_filing_status:
            p_filing_status = p_manual_filing_status

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
    p_child_support = _pi(line, "p_child_support")

    # Student
    s_agi = _pi(line, "s_agi")
    s_tax = _pi(line, "s_tax")
    s_wages = _pi(line, "s_wages")
    s_agi_fti = _pi(line, "s_agi_fti")
    s_earned_fti = _pi(line, "s_earned_fti")
    s_tax_fti = _pi(line, "s_tax_fti")
    s_taxable_scholarships = _pi(line, "s_taxable_scholarships")
    s_foreign_income_exclusion = _pi(line, "s_foreign_income_exclusion")
    s_work_study = _pi(line, "s_work_study")
    s_total_income = _pi(line, "student_total_income")
    has_student_total_income_proxy = False
    if _has_value(line, "s_agi_fti"):
        s_agi = s_agi_fti
    elif _has_value(line, "student_total_income"):
        s_agi = s_total_income
        has_student_total_income_proxy = True
    if _has_value(line, "s_tax_fti"):
        s_tax = s_tax_fti
    if has_student_total_income_proxy:
        s_taxable_scholarships = 0
        s_foreign_income_exclusion = 0
        s_work_study = 0

    # Test ISIR reconstruction proxy: the fixed-width records expose generated
    # parent total income, but not always the wage inputs needed for payroll and
    # employment allowances. Student records similarly expose generated total
    # income separately from wage inputs. Keep raw earned-income fields as the
    # payroll proxy rather than treating generated total income as wages.
    has_parent_earned_income_source = (
        p_earned_income > 0
        or p_spouse_earned_income > 0
        or _has_value(line, "p_spouse_tax_fti")
    )
    if p_earned_income > 0:
        p1_wages = p_earned_income
    elif has_parent_earned_income_source:
        p1_wages = 0
    else:
        p1_wages = p_agi
    if _has_value(line, "s_earned_fti"):
        s_earned = s_earned_fti
    else:
        s_earned = s_wages if s_wages > 0 else s_agi

    return DependentFamily(
        parent_agi=p_agi,
        parent_deductible_ira_payments=p_ira,
        parent_income_tax_paid=p_tax,
        parent_earned_income_p1=p1_wages,
        parent_earned_income_p2=p_spouse_earned_income,
        parent_cash_savings=p_cash,
        parent_investment_net_worth=p_invest,
        parent_business_farm_net_worth=p_bus,
        parent_child_support_received=p_child_support,
        family_size=family_size,
        num_parents=num_parents,
        parent_filing_status=p_filing_status,
        student_agi=s_agi,
        student_foreign_income_exclusion=s_foreign_income_exclusion,
        student_taxable_scholarships=s_taxable_scholarships,
        student_work_study=s_work_study,
        student_income_tax_paid=s_tax,
        student_earned_income=s_earned,
    )


def _is_dependent_record(line: str) -> bool:
    return len(line) >= 7700 and line[187:188] == "A"


def _parent_input_source(line: str) -> str:
    if (
        _pi(line, "p_agi_fti")
        or _pi(line, "p_earned_fti")
        or _pi(line, "p_tax_fti")
        or _pi(line, "p_ira_fti")
        or _pi(line, "p_spouse_earned_fti")
        or _pi(line, "p_spouse_tax_fti")
    ):
        return "parent_fti"
    return "no_parent_fti"


def _parent_wage_proxy_source(line: str, family: DependentFamily) -> str:
    """Describe the source used for parent earned income reconstruction."""
    if _has_value(line, "p_earned_fti") or _has_value(line, "p_spouse_earned_fti"):
        return "parent_fti_earned_income"
    if family.parent_earned_income_p1 or family.parent_earned_income_p2:
        return "parent_total_income_proxy"
    return "none"


def _parent_fti_source_context(line: str) -> dict[str, int]:
    """Expose raw parent FTI source fields for debugging red ISIR records."""
    return {
        "parent_filing_status_fti": _pi(line, "p_filing_status_fti"),
        "parent_agi_fti": _pi(line, "p_agi_fti"),
        "parent_earned_fti": _pi(line, "p_earned_fti"),
        "parent_tax_fti": _pi(line, "p_tax_fti"),
        "parent_education_credits_fti": _pi(line, "p_education_credits_fti"),
        "parent_untaxed_ira_distributions_fti": _pi(line, "p_untaxed_ira_distributions_fti"),
        "parent_spouse_filing_status_fti": _pi(line, "p_spouse_filing_status_fti"),
        "parent_spouse_agi_fti": _pi(line, "p_spouse_agi_fti"),
        "parent_spouse_earned_fti": _pi(line, "p_spouse_earned_fti"),
        "parent_spouse_tax_fti": _pi(line, "p_spouse_tax_fti"),
        "parent_spouse_education_credits_fti": _pi(line, "p_spouse_education_credits_fti"),
        "parent_spouse_untaxed_ira_distributions_fti": _pi(line, "p_spouse_untaxed_ira_distributions_fti"),
    }


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
        parent_wage_proxy_source = _parent_wage_proxy_source(line, family)
        
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
                "parent_wage_proxy_source": parent_wage_proxy_source,
                "parent_earned_income_p1": family.parent_earned_income_p1,
                "parent_earned_income_p2": family.parent_earned_income_p2,
                "parent_fti_source_context": _parent_fti_source_context(line),
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
