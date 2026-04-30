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
    valid_fields = {f.name for f in fields(DependentFamily)}
    
    # Handle detailed reasoning dictionary structure
    facts = {}
    for k, v in raw.items():
        if k in valid_fields and isinstance(v, dict) and "value" in v:
            facts[k] = v["value"]
        elif k in valid_fields and isinstance(v, (int, float)):
            facts[k] = int(v)
            
    # --- DETERMINISTIC CONFIRMATION LOOP ---
    while True:
        print("\n[VERIFY EXTRACTED FACTS]")
        if not facts:
            print("  (no facts extracted)")
        else:
            for k, v in facts.items():
                print(f"  {k:30}: {v:,}")
        
        confirm = input("\nAre these facts correct? [Y]es, [N]o, or type 'key=value' to fix: ").strip().lower()
        if confirm == 'y' or not confirm:
            break
        elif '=' in confirm:
            try:
                k, v = confirm.split('=')
                k = k.strip()
                v = int(v.strip().replace(',', '').replace('$', ''))
                if k in valid_fields:
                    facts[k] = v
                    print(f"  → Updated {k} to {v:,}")
                else:
                    print(f"  ❌ Unknown field: {k}")
            except ValueError:
                print("  ❌ Invalid format. Use 'field=12345'")
        else:
            print("\nTo fix a value, type e.g. 'parent_agi=90000'")

    family = DependentFamily(**facts)

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
