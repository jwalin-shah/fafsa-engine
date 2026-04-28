#!/usr/bin/env python3
"""FAFSA SAI pipeline: natural language → facts → proof → narration → verification.

Usage:
    python demo.py "My parents make $80k, family of 4"
    FAFSA_LLM=claude <set ANTHROPIC_API_KEY> python demo.py "..."
    FAFSA_LLM=openai <set OPENAI_API_KEY> python demo.py "..."
"""
import sys
from dataclasses import fields

from fafsa.kb import DependentFamily, fmt_trace, prove_sai
from fafsa.validate import verify
from llm.base import get_backend


def run(query: str) -> None:
    backend = get_backend()

    print(f"\n{'=' * 60}")
    print(f"Query: {query}")
    print("=" * 60)

    # 1. Extract facts from natural language
    print("\n[1/4] Extracting facts...")
    raw = backend.extract_facts(query)
    valid = {f.name for f in fields(DependentFamily)}
    facts = {k: v for k, v in raw.items() if k in valid}
    family = DependentFamily(**facts)
    if facts:
        for k, v in facts.items():
            print(f"  {k}: {v}")
    else:
        print("  (no facts extracted — using defaults)")

    # 2. Compute proof
    print("\n[2/4] Computing SAI proof...")
    trace = prove_sai(family)
    print(fmt_trace(trace))

    # 3. Narrate in plain English
    print("\n[3/4] Generating explanation...")
    narration = backend.narrate_proof(trace)
    print(f"\n{narration}")

    # 4. Verify against validated dataset
    print("\n[4/4] Verifying...")
    result = verify(trace)
    print(result.message)
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python demo.py "My parents make $80k, family of 4"')
        sys.exit(1)
    run(" ".join(sys.argv[1:]))
