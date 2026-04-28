"""Sweep parent income $40k→$200k and show how SAI changes.

Usage: python examples/counterfactual.py
"""
from dataclasses import replace
from fafsa.kb import DependentFamily, prove_sai

BASE = DependentFamily(family_size=4, num_parents=2, older_parent_age=45)

print(f"{'Parent AGI':>14}  {'SAI':>8}")
print("-" * 26)
for income in range(40_000, 200_001, 10_000):
    family = replace(BASE, parent_agi=income, parent_earned_income_p1=income)
    trace = prove_sai(family)
    print(f"  ${income:>12,}  {trace.sai:>8,}")
