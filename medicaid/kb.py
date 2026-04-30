"""
Medicaid Eligibility Knowledge Base — MAGI (Modified Adjusted Gross Income) rules.

Architecture: 
  Uses the same proof-trace pattern as the FAFSA engine.
  Determines eligibility based on Federal Poverty Level (FPL) percentages.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from fafsa.kb import CitedValue, SAITrace # Reusing structures for demo consistency


@dataclass
class Household:
    state: str = "CA"
    size: int = 1
    annual_income: int = 0
    is_pregnant: bool = False
    is_blind_disabled: bool = False


# 2024 Federal Poverty Level (FPL) Guidelines (Simplified)
# Source: https://aspe.hhs.gov/topics/poverty-economic-mobility/poverty-guidelines
FPL_BASE = 15060
FPL_PER_PERSON = 5380

# Medicaid Expansion Threshold: 138% FPL
EXPANSION_RATE = 1.38


def prove_medicaid(house: Household) -> SAITrace:
    steps: list[CitedValue] = []
    def step(label, value, citation, formula):
        cv = CitedValue(label, value, citation, formula)
        steps.append(cv)
        return value

    # 1. Calculate FPL for household size
    fpl_guideline = step(
        "federal_poverty_level",
        FPL_BASE + (house.size - 1) * FPL_PER_PERSON,
        "2024 HHS Poverty Guidelines",
        f"{FPL_BASE} + ({house.size}-1) * {FPL_PER_PERSON}"
    )

    # 2. Determine threshold (138% for expansion states)
    threshold = step(
        "eligibility_threshold",
        int(fpl_guideline * EXPANSION_RATE),
        "Affordable Care Act (138% FPL)",
        f"FPL * {EXPANSION_RATE}"
    )

    # 3. Income check
    is_eligible = house.annual_income <= threshold
    
    # We'll use SAI field to represent "Eligibility Score" (1 for Yes, 0 for No) for demo purposes
    # or just hijack the trace to show the logic.
    step(
        "medicaid_eligible",
        1 if is_eligible else 0,
        "State Medicaid Rules",
        f"income ({house.annual_income}) <= threshold ({threshold})"
    )

    return SAITrace(sai=(1 if is_eligible else 0), steps=steps, family=None)


def fmt_medicaid_trace(trace: SAITrace) -> str:
    eligible = "✅ ELIGIBLE" if trace.sai == 1 else "❌ NOT ELIGIBLE"
    lines = [f"Result: {eligible}", ""]
    for s in trace.steps:
        lines.append(f"  {s.label:25}: {s.value:,} [{s.citation}]")
    return "\n".join(lines)
