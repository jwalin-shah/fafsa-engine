import pytest
from fafsa.kb import DependentFamily, SAITrace, CitedValue, prove_sai, prove_sai_counterfactual, fmt_trace


def test_prove_sai_returns_trace():
    family = DependentFamily(parent_agi=80_000, family_size=4)
    trace = prove_sai(family)
    assert isinstance(trace, SAITrace)
    assert isinstance(trace.sai, int)
    assert len(trace.steps) > 0


def test_prove_sai_stores_family():
    family = DependentFamily(parent_agi=80_000, family_size=4)
    trace = prove_sai(family)
    assert trace.family is family


def test_zero_income_non_positive_sai():
    family = DependentFamily()
    trace = prove_sai(family)
    assert trace.sai <= 0


def test_high_income_positive_sai():
    family = DependentFamily(parent_agi=200_000, family_size=3)
    trace = prove_sai(family)
    assert trace.sai > 0


def test_counterfactual_higher_income_raises_sai():
    family = DependentFamily(parent_agi=60_000, family_size=4)
    base = prove_sai(family)
    cf = prove_sai_counterfactual(family, {"parent_agi": 120_000})
    assert cf.sai > base.sai


def test_fmt_trace_contains_sai():
    family = DependentFamily(parent_agi=80_000, family_size=4)
    trace = prove_sai(family)
    result = fmt_trace(trace)
    assert isinstance(result, str)
    assert len(result) > 0
    assert f"${trace.sai:,}" in result


def test_steps_are_cited_values():
    family = DependentFamily(parent_agi=80_000, family_size=4)
    trace = prove_sai(family)
    for step in trace.steps:
        assert isinstance(step, CitedValue)
        assert step.citation
        assert step.formula
