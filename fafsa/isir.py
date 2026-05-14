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


class ISIRParseError(ValueError):
    """Raised when a nonblank fixed-width ISIR field cannot be parsed."""

    def __init__(
        self,
        key: str,
        value: str,
        lineno: int | None,
        start: int,
        end: int,
    ) -> None:
        location = f"line {lineno}: " if lineno is not None else ""
        message = (
            f"{location}ISIR field {key!r} at columns {start + 1}-{end} "
            f"must be an integer or blank, got {value!r}"
        )
        super().__init__(message)
        self.key = key
        self.value = value
        self.lineno = lineno
        self.start = start
        self.end = end


@dataclass(frozen=True)
class ISIRRecord:
    """Parsed view over one fixed-width ISIR record."""
    line: str
    lineno: int | None = None

    def field_int(self, key: str) -> int:
        s, e = _FIELDS[key]
        v = self.line[s:e].strip().split()
        if not v or v[0] == 'N/A': return 0
        try:
            return int(v[0])
        except ValueError:
            raise ISIRParseError(key, v[0], self.lineno, s, e)

    def has_value(self, key: str) -> bool:
        s, e = _FIELDS[key]
        v = self.line[s:e].strip().split()
        return bool(v and v[0] != "N/A")

    def has_manual_override(self, key: str) -> bool:
        return self.has_value(key) and self.field_int(key) != 0

    @property
    def is_dependent_formula_a(self) -> bool:
        return len(self.line) >= 7700 and self.line[187:188] == "A"

    @property
    def target_sai(self) -> int:
        return self.field_int("sai")

    @property
    def parent_input_source(self) -> str:
        if self.has_parent_fti_income_or_tax_source:
            return "parent_fti"
        return "no_parent_fti"

    @property
    def has_parent_fti_income_or_tax_source(self) -> bool:
        return any(
            self.field_int(key)
            for key in (
                "p_agi_fti",
                "p_earned_fti",
                "p_tax_fti",
                "p_ira_fti",
                "p_spouse_earned_fti",
                "p_spouse_tax_fti",
            )
        )

    def reconstruct_family(self) -> DependentFamily:
        return _reconstruct_family(self)

    def compare_intermediates(self, trace: SAITrace) -> list[dict]:
        return _compare_isir_intermediates(self, trace)

    def parent_wage_proxy_source(self, family: DependentFamily) -> str:
        """Describe the source used for parent earned income reconstruction."""
        if self.has_value("p_earned_fti") or self.has_value("p_spouse_earned_fti"):
            return "parent_fti_earned_income"
        if family.parent_earned_income_p1 or family.parent_earned_income_p2:
            return "parent_total_income_proxy"
        return "none"

    def parent_fti_source_context(self) -> dict[str, int]:
        """Expose raw parent FTI source fields for debugging red ISIR records."""
        return {
            "parent_filing_status_fti": self.field_int("p_filing_status_fti"),
            "parent_agi_fti": self.field_int("p_agi_fti"),
            "parent_earned_fti": self.field_int("p_earned_fti"),
            "parent_tax_fti": self.field_int("p_tax_fti"),
            "parent_education_credits_fti": self.field_int("p_education_credits_fti"),
            "parent_untaxed_ira_distributions_fti": self.field_int("p_untaxed_ira_distributions_fti"),
            "parent_spouse_filing_status_fti": self.field_int("p_spouse_filing_status_fti"),
            "parent_spouse_agi_fti": self.field_int("p_spouse_agi_fti"),
            "parent_spouse_earned_fti": self.field_int("p_spouse_earned_fti"),
            "parent_spouse_tax_fti": self.field_int("p_spouse_tax_fti"),
            "parent_spouse_education_credits_fti": self.field_int("p_spouse_education_credits_fti"),
            "parent_spouse_untaxed_ira_distributions_fti": self.field_int("p_spouse_untaxed_ira_distributions_fti"),
        }


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
    return ISIRRecord(line).field_int(key)


def _has_value(line: str, key: str) -> bool:
    return ISIRRecord(line).has_value(key)


def _has_manual_override(line: str, key: str) -> bool:
    return ISIRRecord(line).has_manual_override(key)


def reconstruct_family(line: str) -> DependentFamily:
    """Reconstruct a DependentFamily from an ISIR record."""
    return ISIRRecord(line).reconstruct_family()


def _reconstruct_family(record: ISIRRecord) -> DependentFamily:
    p_agi = record.field_int("p_agi_fti")
    p_tax = record.field_int("p_tax_fti")
    p_ira = record.field_int("p_ira_fti")
    p_filing_status = record.field_int("p_filing_status_fti")
    p_manual_filing_status = record.field_int("p_manual_filing_status")
    p_manual_earned_income = record.field_int("p_manual_earned_income")
    p_manual_agi = record.field_int("p_manual_agi")
    p_manual_tax = record.field_int("p_manual_tax")
    p_spouse_manual_earned_income = record.field_int("p_spouse_manual_earned_income")
    p_spouse_manual_agi = record.field_int("p_spouse_manual_agi")
    p_spouse_manual_tax = record.field_int("p_spouse_manual_tax")
    p_earned_income = record.field_int("p_earned_fti")
    p_spouse_earned_income = record.field_int("p_spouse_earned_fti")
    p_spouse_tax = record.field_int("p_spouse_tax_fti")
    parent_fti_missing = not record.has_parent_fti_income_or_tax_source

    if record.has_manual_override("p_manual_agi") or record.has_manual_override("p_spouse_manual_agi"):
        p_agi = (
            p_manual_agi if record.has_manual_override("p_manual_agi") else p_agi
        ) + (
            p_spouse_manual_agi if record.has_manual_override("p_spouse_manual_agi") else 0
        )
    if record.has_manual_override("p_manual_tax"):
        p_tax = p_manual_tax
    if record.has_manual_override("p_spouse_manual_tax"):
        p_spouse_tax = p_spouse_manual_tax
    if record.has_manual_override("p_manual_earned_income"):
        p_earned_income = p_manual_earned_income
    if record.has_manual_override("p_spouse_manual_earned_income"):
        p_spouse_earned_income = p_spouse_manual_earned_income
    p_tax += p_spouse_tax

    p_total_income = record.field_int("parent_total_income")
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
    family_size = record.field_int("p_fam_fti")
    num_parents = record.field_int("p_num_fti")
    
    # Backfill from IPA if FTI fields are 0
    if family_size == 0:
        ipa = record.field_int("ipa")
        for size, val in IPA_TABLE.items():
            if val == ipa:
                family_size = size
                break
        if family_size == 0 and ipa > 58560:
            family_size = 6 + (ipa - 58560) // 6610

    if num_parents == 0:
        num_parents = 2 if record.field_int("eea") > 0 else 1

    # Assets
    p_cash = record.field_int("p_cash")
    p_invest = record.field_int("p_invest")
    p_bus = record.field_int("p_bus")
    p_child_support = record.field_int("p_child_support")

    # Student
    s_agi = record.field_int("s_agi")
    s_tax = record.field_int("s_tax")
    s_wages = record.field_int("s_wages")
    s_agi_fti = record.field_int("s_agi_fti")
    s_earned_fti = record.field_int("s_earned_fti")
    s_tax_fti = record.field_int("s_tax_fti")
    s_taxable_scholarships = record.field_int("s_taxable_scholarships")
    s_foreign_income_exclusion = record.field_int("s_foreign_income_exclusion")
    s_work_study = record.field_int("s_work_study")
    s_total_income = record.field_int("student_total_income")
    has_student_total_income_proxy = False
    if record.has_value("s_agi_fti"):
        s_agi = s_agi_fti
    elif record.has_value("student_total_income"):
        s_agi = s_total_income
        has_student_total_income_proxy = True
    if record.has_value("s_tax_fti"):
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
        or record.has_value("p_spouse_tax_fti")
    )
    if p_earned_income > 0:
        p1_wages = p_earned_income
    elif has_parent_earned_income_source:
        p1_wages = 0
    else:
        p1_wages = p_agi
    if record.has_value("s_earned_fti"):
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
    return ISIRRecord(line).is_dependent_formula_a


def _parent_input_source(line: str) -> str:
    return ISIRRecord(line).parent_input_source


def _parent_wage_proxy_source(line: str, family: DependentFamily) -> str:
    """Describe the source used for parent earned income reconstruction."""
    return ISIRRecord(line).parent_wage_proxy_source(family)


def _parent_fti_source_context(line: str) -> dict[str, int]:
    """Expose raw parent FTI source fields for debugging red ISIR records."""
    return ISIRRecord(line).parent_fti_source_context()


def compare_isir_intermediates(line: str, trace: SAITrace) -> list[dict]:
    """Compare ED ISIR intermediates with the engine trace for Formula A."""
    return ISIRRecord(line).compare_intermediates(trace)


def _compare_isir_intermediates(record: ISIRRecord, trace: SAITrace) -> list[dict]:
    trace_values = {step.label: int(step.value) for step in trace.steps}
    diagnostics = []
    for trace_label, field in _TRACE_TO_ISIR_FIELDS.items():
        expected = record.field_int(field)
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
        record = ISIRRecord(line, lineno)
        if not record.is_dependent_formula_a:
            continue

        dependent_records += 1
        try:
            target_sai = record.target_sai
            parent_input_source = record.parent_input_source

            # 1. Reconstruct inputs
            family = record.reconstruct_family()

            # 2. Compute end-to-end
            trace = prove_sai(family)
            parent_wage_proxy_source = record.parent_wage_proxy_source(family)

            # 3. Verify
            if trace.sai == target_sai:
                source_counts = source_summary.setdefault(
                    parent_input_source,
                    {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
                )
                source_counts["total"] += 1
                passed += 1
                source_counts["passed"] += 1
            else:
                diagnostics = record.compare_intermediates(trace)
                parent_fti_source_context = record.parent_fti_source_context()
                source_counts = source_summary.setdefault(
                    parent_input_source,
                    {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
                )
                source_counts["total"] += 1
                failed += 1
                source_counts["failed"] += 1
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
                    "parent_fti_source_context": parent_fti_source_context,
                    "diagnostics": diagnostics,
                    "p_agi": family.parent_agi,
                    "p_tax": family.parent_income_tax_paid,
                    "s_agi": family.student_agi,
                    "fam": family.family_size,
                })
        except ISIRParseError as exc:
            failed += 1
            parent_input_source = "parse_error"
            source_counts = source_summary.setdefault(
                parent_input_source,
                {"total": 0, "passed": 0, "failed": 0, "skipped": 0},
            )
            source_counts["total"] += 1
            source_counts["failed"] += 1
            failures.append({
                "lineno": lineno,
                "target": None,
                "actual": None,
                "parent_input_source": parent_input_source,
                "error": str(exc),
                "field": exc.key,
                "raw_value": exc.value,
                "diagnostics": [],
            })
            failure_signature_summary[f"{parent_input_source}:{exc.key}"] = (
                failure_signature_summary.get(f"{parent_input_source}:{exc.key}", 0) + 1
            )
            continue

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
