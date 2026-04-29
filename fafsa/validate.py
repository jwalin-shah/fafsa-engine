"""Verification of engine output.

The engine's components (parent contribution schedule, SAI summation, IPA
table) are validated at import time against the U.S. Department of
Education's published 2024-25 test ISIRs. See ``fafsa/isir.py``.

``verify(trace)`` reports whether the engine has been validated and how
many ED test cases it agrees with. It does NOT claim that this specific
input has been independently checked against ED — only that the engine
producing the trace has passed component-level validation against ED's
own test data.
"""
from __future__ import annotations
import math
import random
from dataclasses import dataclass, asdict

from fafsa.kb import DependentFamily, SAITrace, prove_sai
from fafsa.isir import validate_isir_file, ISIRReport


@dataclass
class VerificationResult:
    verified: bool
    message: str


def _ed_round_local(x: float) -> int:
    return math.floor(x + 0.5)


def _rand_int(lo: int, hi: int, zero_prob: float = 0.0) -> int:
    if zero_prob and random.random() < zero_prob:
        return 0
    return random.randint(lo, hi)


def make_family(seed: int | None = None) -> DependentFamily:
    """Generate a reproducible random DependentFamily from a seed.

    Used for regression / smoke testing the engine's determinism. NOT a
    correctness oracle — the families are random, the SAI is whatever
    prove_sai() produces. Real correctness validation is in fafsa/isir.py.
    """
    if seed is not None:
        random.seed(seed)

    family_size = random.choices([2, 3, 4, 5, 6, 7], weights=[5, 30, 30, 20, 10, 5])[0]
    num_parents = random.choices([1, 2], weights=[25, 75])[0]
    older_parent_age = random.randint(35, 65)

    parent_agi = _rand_int(0, 300_000)
    eff_rate = random.uniform(0.05, 0.25)
    parent_tax = _ed_round_local(parent_agi * eff_rate)

    p1_wages = _rand_int(0, parent_agi, zero_prob=0.05)
    p2_wages = _rand_int(0, max(0, parent_agi - p1_wages), zero_prob=0.3) if num_parents == 2 else 0

    parent_ira = _rand_int(0, 20_000, zero_prob=0.8)
    parent_pension = _rand_int(0, 30_000, zero_prob=0.85)
    parent_tex_int = _rand_int(0, 5_000, zero_prob=0.85)

    p_cash = _rand_int(0, 100_000, zero_prob=0.1)
    p_inv = _rand_int(0, 400_000, zero_prob=0.3)
    p_biz = _rand_int(0, 200_000, zero_prob=0.8)
    p_cs = _rand_int(0, 15_000, zero_prob=0.85)

    s_agi = _rand_int(0, 30_000, zero_prob=0.3)
    s_wages = _rand_int(0, s_agi, zero_prob=0.1)
    s_tax = _ed_round_local(s_agi * random.uniform(0.0, 0.15))

    s_cash = _rand_int(0, 20_000, zero_prob=0.5)
    s_inv = _rand_int(0, 30_000, zero_prob=0.8)

    return DependentFamily(
        parent_agi=parent_agi,
        parent_income_tax_paid=parent_tax,
        parent_earned_income_p1=p1_wages,
        parent_earned_income_p2=p2_wages,
        parent_untaxed_ira_distributions=parent_ira,
        parent_untaxed_pension=parent_pension,
        parent_tax_exempt_interest=parent_tex_int,
        parent_cash_savings=p_cash,
        parent_investment_net_worth=p_inv,
        parent_business_farm_net_worth=p_biz,
        parent_child_support_received=p_cs,
        family_size=family_size,
        num_parents=num_parents,
        older_parent_age=older_parent_age,
        student_agi=s_agi,
        student_income_tax_paid=s_tax,
        student_earned_income=s_wages,
        student_cash_savings=s_cash,
        student_investment_net_worth=s_inv,
    )


# ---------------------------------------------------------------------------
# ED ground-truth validation (cached)
# ---------------------------------------------------------------------------

_ISIR_REPORT: ISIRReport | None = None


def _get_isir_report() -> ISIRReport:
    """Run ISIR validation once per process and cache the result."""
    global _ISIR_REPORT
    if _ISIR_REPORT is None:
        _ISIR_REPORT = validate_isir_file()
    return _ISIR_REPORT


def verify(trace: SAITrace) -> VerificationResult:
    """Report engine validation status for a computed trace.

    The engine's components are validated against ED's published 2024-25 test
    ISIRs (see fafsa/isir.py). This function reports that validation status
    alongside the trace's SAI value.

    It does NOT claim that this specific input was independently verified
    against ED — only that the engine producing the result has passed
    component-level validation on ED's own test data.
    """
    if trace.family is None:
        return VerificationResult(
            verified=False,
            message="⚠️ unverified (no input family stored in trace)",
        )

    report = _get_isir_report()

    if report.failed > 0:
        return VerificationResult(
            verified=False,
            message=(
                f"❌ engine FAILED ED validation: "
                f"{report.passed}/{report.total} ED test ISIRs pass, "
                f"{report.failed} fail. Engine output is not trustworthy."
            ),
        )

    return VerificationResult(
        verified=True,
        message=(
            f"✅ engine validated against {report.passed}/{report.total} "
            f"ED test ISIRs (parent contribution schedule, SAI summation, "
            f"IPA table). This specific input was computed by the same engine "
            f"but was not independently checked against ED."
        ),
    )
