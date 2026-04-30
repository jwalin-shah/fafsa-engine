"""
FAFSA SAI Knowledge Base — Formula A, B, and C

Architecture: hybrid.
  - Python arithmetic implements the EFC formula exactly
  - Every computed value carries a CitedValue with an ED citation string
  - prove_sai(family) returns a full computation trace — the "proof" IS
    the auditable derivation the spec requires

Formula source: 2024-25 Pell Eligibility and SAI Guide Version 4 (March 2024), Federal Student Aid
  https://fsapartners.ed.gov/sites/default/files/2024-01/20242025FAFSAPellEligibilityandSAIGuide.pdf
"""

from __future__ import annotations
import math
from dataclasses import dataclass, replace as dc_replace


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DependentFamily:
    """Inputs for a dependent student SAI calculation (Formula A)."""
    parent_agi: int = 0
    parent_deductible_ira_payments: int = 0
    parent_tax_exempt_interest: int = 0
    parent_untaxed_ira_distributions: int = 0
    parent_untaxed_pension: int = 0
    parent_foreign_income_exclusion: int = 0
    parent_taxable_scholarships: int = 0
    parent_education_credits: int = 0
    parent_work_study: int = 0
    parent_income_tax_paid: int = 0
    parent_earned_income_p1: int = 0
    parent_earned_income_p2: int = 0
    parent_cash_savings: int = 0
    parent_investment_net_worth: int = 0
    parent_business_farm_net_worth: int = 0
    parent_child_support_received: int = 0
    family_size: int = 3
    num_parents: int = 2
    older_parent_age: int = 45
    student_agi: int = 0
    student_deductible_ira_payments: int = 0
    student_tax_exempt_interest: int = 0
    student_untaxed_ira_distributions: int = 0
    student_untaxed_pension: int = 0
    student_foreign_income_exclusion: int = 0
    student_taxable_scholarships: int = 0
    student_education_credits: int = 0
    student_work_study: int = 0
    student_income_tax_paid: int = 0
    student_earned_income: int = 0
    student_cash_savings: int = 0
    student_investment_net_worth: int = 0
    student_business_farm_net_worth: int = 0
    max_pell_eligible: bool = False


@dataclass
class IndependentFamily:
    """Inputs for an independent student SAI calculation (Formula B or C)."""
    student_agi: int = 0
    student_deductible_ira_payments: int = 0
    student_tax_exempt_interest: int = 0
    student_untaxed_ira_distributions: int = 0
    student_untaxed_pension: int = 0
    student_foreign_income_exclusion: int = 0
    student_taxable_scholarships: int = 0
    student_education_credits: int = 0
    student_work_study: int = 0
    student_income_tax_paid: int = 0
    student_earned_income: int = 0
    spouse_earned_income: int = 0
    student_cash_savings: int = 0
    student_investment_net_worth: int = 0
    student_business_farm_net_worth: int = 0
    student_child_support_received: int = 0
    family_size: int = 1
    is_married: bool = False
    has_dependents: bool = False
    older_student_age: int = 25


@dataclass
class CitedValue:
    label: str
    value: float
    citation: str
    formula: str


@dataclass
class SAITrace:
    sai: int
    steps: list[CitedValue]
    auto_neg1500: bool = False
    family: DependentFamily | IndependentFamily | None = None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REF = "2024-25 SAI Guide Version 4"
IPA_TABLE: dict[int, int] = {2: 27_600, 3: 34_350, 4: 42_430, 5: 50_060, 6: 58_560}
IPA_ADDITIONAL = 6_610
AAI_SCHEDULE = [
    (-6820,  20600,     0,    0.22,     0),
    (20601,  25800,  4532,    0.25, 20600),
    (25801,  31000,  5832,    0.29, 25800),
    (31001,  36300,  7340,    0.34, 31000),
    (36301,  41500,  9142,    0.40, 36300),
    (41501, 999999, 11222,    0.47, 41500),
]
OASDI_RATE = 0.062
OASDI_BASE_SINGLE = 147_000
OASDI_BASE_JOINT  = 294_000
MEDICARE_RATE_LOW  = 0.0145
MEDICARE_RATE_HIGH = 0.0235
MEDICARE_THRESHOLD_SINGLE = 200_000
MEDICARE_THRESHOLD_JOINT  = 250_000
EEA_MAX = 4_730
EEA_RATE = 0.35
STUDENT_IPA = 11_130
PARENT_ASSET_RATE  = 0.12
STUDENT_ASSET_RATE = 0.20
STUDENT_INCOME_RATE = 0.50

IPA_B_SINGLE = 11_130
IPA_B_MARRIED = 17_840
IPA_C_TABLE: dict[int, int] = {2: 38_180, 3: 47_510, 4: 58_680, 5: 69_240, 6: 80_440}
IPA_C_ADDITIONAL = 9_140


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ed_round(x: float) -> int:
    return math.floor(x + 0.5)

def _ipa(family_size: int) -> int:
    if family_size <= 2: return IPA_TABLE[2]
    if family_size <= 6: return IPA_TABLE[family_size]
    return IPA_TABLE[6] + (family_size - 6) * IPA_ADDITIONAL

def _apa(age: int, num_parents: int) -> int:
    return 0

def _medicare(wages: int, is_joint: bool) -> int:
    threshold = MEDICARE_THRESHOLD_JOINT if is_joint else MEDICARE_THRESHOLD_SINGLE
    if wages <= threshold: return _ed_round(wages * MEDICARE_RATE_LOW)
    return _ed_round(threshold * MEDICARE_RATE_LOW + (wages - threshold) * MEDICARE_RATE_HIGH)

def _oasdi(wages: int, is_joint: bool) -> int:
    base = OASDI_BASE_JOINT if is_joint else OASDI_BASE_SINGLE
    return _ed_round(min(wages, base) * OASDI_RATE)

def _business_farm_adjustment(net_worth: int) -> int:
    if net_worth < 1: return 0
    if net_worth <= 165_000: return _ed_round(net_worth * 0.40)
    if net_worth <= 490_000: return _ed_round(66_000 + (net_worth - 165_000) * 0.50)
    if net_worth <= 820_000: return _ed_round(228_500 + (net_worth - 490_000) * 0.60)
    return _ed_round(426_500 + (net_worth - 820_000) * 1.00)

def _aai_to_parent_contribution(aai: int) -> int:
    if aai < -6_820: return -1_500
    for lower, upper, base, rate, base_lower in AAI_SCHEDULE:
        if lower <= aai <= upper: return _ed_round(base + (aai - base_lower) * rate)
    _, _, base, rate, base_lower = AAI_SCHEDULE[-1]
    return _ed_round(base + (aai - base_lower) * rate)


# ---------------------------------------------------------------------------
# Formulas
# ---------------------------------------------------------------------------

def prove_sai(family: DependentFamily | IndependentFamily) -> SAITrace:
    if isinstance(family, IndependentFamily):
        return _prove_sai_independent(family)
    return _prove_sai_dependent(family)


def _prove_sai_dependent(family: DependentFamily) -> SAITrace:
    steps: list[CitedValue] = []
    def step(label, value, citation, formula):
        cv = CitedValue(label, value, citation, formula)
        steps.append(cv)
        return value

    # Parent Income
    p_add = step("parent_income_additions", family.parent_agi + family.parent_deductible_ira_payments + family.parent_tax_exempt_interest + max(0, family.parent_untaxed_ira_distributions) + max(0, family.parent_untaxed_pension) + max(0, family.parent_foreign_income_exclusion), f"{REF}, Formula A, Line 1", "sum")
    p_off = step("parent_income_offsets", family.parent_taxable_scholarships + family.parent_education_credits + family.parent_work_study, f"{REF}, Formula A, Line 2", "sum")
    p_total = step("parent_total_income", p_add - p_off, f"{REF}, Formula A, Line 3", "line 1 - line 2")
    
    is_joint = family.num_parents == 2
    combined_wages = family.parent_earned_income_p1 + family.parent_earned_income_p2
    p_tax = step("parent_income_tax_paid", family.parent_income_tax_paid, f"{REF}, Line 4", "input")
    p_pay = step("parent_payroll_tax", _medicare(combined_wages, is_joint) + _oasdi(combined_wages, is_joint), f"{REF}, Line 5", "Table A1")
    p_ipa = step("parent_income_protection_allowance", _ipa(family.family_size), f"{REF}, Line 6", "Table A2")
    p_eea = step("parent_employment_expense_allowance", min(_ed_round(combined_wages * EEA_RATE), EEA_MAX) if combined_wages > 0 else 0, f"{REF}, Line 7", "35% max 4730")
    p_total_allow = step("parent_total_allowances", p_tax + p_pay + p_ipa + p_eea, f"{REF}, Line 8", "sum")
    pai = step("parent_available_income", p_total - p_total_allow, f"{REF}, Line 9", "total - allowances")

    # Parent Assets
    p_nw = step("parent_net_worth", family.parent_child_support_received + family.parent_cash_savings + max(0, family.parent_investment_net_worth) + _business_farm_adjustment(family.parent_business_farm_net_worth), f"{REF}, Line 14", "sum")
    p_apa = step("parent_asset_protection_allowance", 0, f"{REF}, Line 15", "Table A4 (0)")
    pca = step("parent_contribution_from_assets", max(0, _ed_round((p_nw - p_apa) * PARENT_ASSET_RATE)), f"{REF}, Lines 16-17", "12% adjustment")
    
    paai = step("parent_adjusted_available_income", pai + pca, f"{REF}, Line 18", "PAI + PCA")
    pc = step("parent_contribution", _aai_to_parent_contribution(int(paai)), f"{REF}, Line 19", "Table A5")

    # Student Income
    s_add = step("student_income_additions", family.student_agi + family.student_deductible_ira_payments + family.student_tax_exempt_interest + max(0, family.student_untaxed_ira_distributions) + max(0, family.student_untaxed_pension) + max(0, family.student_foreign_income_exclusion), f"{REF}, Line 20", "sum")
    s_off = step("student_income_offsets", family.student_taxable_scholarships + family.student_education_credits + family.student_work_study, f"{REF}, Line 21", "sum")
    s_total = step("student_total_income", s_add - s_off, f"{REF}, Line 22", "sum")
    
    s_pay = step("student_payroll_tax", _medicare(family.student_earned_income, False) + _oasdi(family.student_earned_income, False), f"{REF}, Line 24", "Table A1")
    s_ipa = STUDENT_IPA
    paai_neg = step("parents_negative_paai_allowance", max(0, -paai), f"{REF}, Line 26", "if PAAI < 0")
    s_total_allow = step("student_total_allowances", family.student_income_tax_paid + s_pay + s_ipa + paai_neg, f"{REF}, Line 27", "sum")
    s_avail = step("student_available_income", s_total - s_total_allow, f"{REF}, Line 28", "total - allow")
    sci = step("student_contribution_from_income", max(-1500, _ed_round(s_avail * STUDENT_INCOME_RATE)), f"{REF}, Line 30", "50% floor -1500")

    # Student Assets
    s_nw = step("student_net_worth", family.student_cash_savings + max(0, family.student_investment_net_worth) + _business_farm_adjustment(family.student_business_farm_net_worth), f"{REF}, Line 34", "sum")
    sca = step("student_contribution_from_assets", max(0, _ed_round(s_nw * STUDENT_ASSET_RATE)), f"{REF}, Line 36", "20%")

    sai = max(-1_500, int(pc + sci + sca))
    step("student_aid_index", sai, f"{REF}, Line 37", "sum")

    return SAITrace(sai=sai, steps=steps, family=family)


def _prove_sai_independent(family: IndependentFamily) -> SAITrace:
    steps: list[CitedValue] = []
    def step(label, value, citation, formula):
        cv = CitedValue(label, value, citation, formula)
        steps.append(cv)
        return value

    s_add = step("student_income_additions", family.student_agi + family.student_deductible_ira_payments + family.student_tax_exempt_interest + max(0, family.student_untaxed_ira_distributions) + max(0, family.student_untaxed_pension) + max(0, family.student_foreign_income_exclusion), f"{REF}, Line 1", "sum")
    s_off = step("student_income_offsets", family.student_taxable_scholarships + family.student_education_credits + family.student_work_study, f"{REF}, Line 2", "sum")
    s_total = step("student_total_income", s_add - s_off, f"{REF}, Line 3", "sum")

    combined_wages = family.student_earned_income + family.spouse_earned_income
    is_joint = family.is_married
    s_pay = step("student_payroll_tax", _medicare(combined_wages, is_joint) + _oasdi(combined_wages, is_joint), f"{REF}, Line 5", "Table A1")
    
    if family.has_dependents:
        ipa = IPA_C_TABLE.get(family.family_size, IPA_C_TABLE[6] + (family.family_size - 6) * IPA_C_ADDITIONAL)
    else:
        ipa = IPA_B_MARRIED if family.is_married else IPA_B_SINGLE
    
    s_ipa = step("student_income_protection_allowance", ipa, f"{REF}, Line 6", "Table B2/C2")
    s_eea = step("student_employment_expense_allowance", min(_ed_round(combined_wages * EEA_RATE), EEA_MAX) if combined_wages > 0 else 0, f"{REF}, Line 7", "sum")
    total_allow = step("student_total_allowances", family.student_income_tax_paid + s_pay + s_ipa + s_eea, f"{REF}, Line 8", "sum")
    avail_inc = step("student_available_income", s_total - total_allow, f"{REF}, Line 9", "total - allow")

    s_nw = step("student_net_worth", family.student_child_support_received + family.student_cash_savings + max(0, family.student_investment_net_worth) + _business_farm_adjustment(family.student_business_farm_net_worth), f"{REF}, Line 14", "sum")
    s_apa = step("student_asset_protection_allowance", 0, f"{REF}, Line 15", "Table A4 (0)")
    sca = step("student_contribution_from_assets", max(0, _ed_round((s_nw - s_apa) * PARENT_ASSET_RATE)), f"{REF}, Line 17", "12%")

    if family.has_dependents:
        sai_raw = _aai_to_parent_contribution(int(avail_inc + sca))
    else:
        sai_raw = int(avail_inc + sca)
        
    sai = max(-1_500, sai_raw)
    step("student_aid_index", sai, f"{REF}, Final", "Final sum")

    return SAITrace(sai=sai, steps=steps, family=family)


def prove_sai_counterfactual(family: DependentFamily | IndependentFamily, overrides: dict) -> SAITrace:
    return prove_sai(dc_replace(family, **overrides))


def fmt_trace(trace: SAITrace, verbose: bool = False) -> str:
    lines = [f"  SAI = ${trace.sai:,}"]
    if verbose:
        for s in trace.steps:
            lines.append(f"    {s.label:50s} = {s.value:>10,}  [{s.citation}]")
    return "\n".join(lines)
