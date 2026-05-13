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


from fafsa.validate import VerificationResult, make_family, verify


def test_verify_reports_unverified_when_isir_validation_is_red():
    """When local ED test ISIR validation is red, verify() must say so."""
    family = make_family(0)
    trace = prove_sai(family)
    result = verify(trace)
    assert isinstance(result, VerificationResult)
    assert not result.verified
    assert "FAILED ED validation" in result.message
    assert "not trustworthy" in result.message


def test_verify_message_mentions_current_isir_count():
    """Verify message must cite the current ED ISIR validation count."""
    family = make_family(42)
    trace = prove_sai(family)
    result = verify(trace)
    assert "33/42" in result.message
    assert "Formula A dependent ED records" in result.message


def test_verify_without_family_is_unverified():
    from fafsa.kb import SAITrace, CitedValue
    trace = SAITrace(sai=0, steps=[], family=None)
    result = verify(trace)
    assert not result.verified
