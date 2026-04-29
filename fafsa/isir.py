"""ED test ISIR validation.

Validates the engine's components against the U.S. Department of Education's
official 2024-25 test ISIR records (Institutional Student Information Records).

Source: https://github.com/usedgov/fafsa-test-isirs-2024-25
File:   data/IDSA25OP-20240308.txt

Per-record checks (Formula A — dependent student records only):
    1. _aai_to_parent_contribution(PAAI) == ISIR Parent Contribution
    2. PC + SCI + SCA == SAI (formula summation integrity)
    3. IPA value in ISIR exists in our IPA_TABLE

These are component-level checks. They confirm that the engine's parent
contribution schedule, SAI summation, and IPA table all agree with ED's own
test data. They do NOT cover end-to-end input → SAI for arbitrary user input
(that requires reconstructing ~19 input fields per record, which is future work).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fafsa.kb import IPA_TABLE, _aai_to_parent_contribution


_DEFAULT_ISIR_PATH = Path(__file__).parent.parent / "data" / "IDSA25OP-20240308.txt"


# Field positions in the 2024-25 ISIR fixed-width layout
_FIELDS = {
    "sai":     (175, 181),
    "formula": (187, 188),
    "ipa":     (2895, 2910),
    "eea":     (2910, 2925),
    "paai":    (2940, 2955),
    "pc":      (2955, 2970),
    "sci":     (3060, 3075),
    "sca":     (3162, 3174),
    "fam":     (3177, 3180),
}


@dataclass
class ISIRReport:
    """Result of running validation across an ISIR test file."""
    total: int
    passed: int
    failed: int
    skipped: int
    failures: list[dict]

    @property
    def all_passed(self) -> bool:
        return self.failed == 0 and self.passed > 0


def _pi(line: str, key: str) -> int | None:
    s, e = _FIELDS[key]
    v = line[s:e].strip()
    return int(v) if v else None


def _is_dependent_record(line: str) -> bool:
    return len(line) >= 3200 and line[187:188] == "A"


def validate_isir_file(path: str | Path | None = None) -> ISIRReport:
    """Run component validation across all Formula A records in an ISIR file."""
    if path is None:
        path = _DEFAULT_ISIR_PATH
    with open(path) as f:
        lines = [l.rstrip("\n") for l in f]

    ipa_values = set(IPA_TABLE.values())
    passed = failed = skipped = 0
    failures: list[dict] = []

    for lineno, line in enumerate(lines, 1):
        if not _is_dependent_record(line):
            continue

        sai  = _pi(line, "sai")
        ipa  = _pi(line, "ipa")
        paai = _pi(line, "paai")
        pc   = _pi(line, "pc")
        sci  = _pi(line, "sci")
        sca  = _pi(line, "sca")

        if paai is None or pc is None or ipa is None:
            skipped += 1
            continue

        our_pc = _aai_to_parent_contribution(paai)
        pc_ok = (our_pc == pc)

        sai_ok = True
        if sai is not None and sci is not None and sca is not None:
            sai_ok = (pc + sci + sca == sai)

        ipa_ok = ipa in ipa_values

        if pc_ok and sai_ok and ipa_ok:
            passed += 1
        else:
            failed += 1
            failures.append({
                "lineno": lineno,
                "ipa": ipa, "paai": paai,
                "pc": pc, "our_pc": our_pc,
                "sai": sai, "sci": sci, "sca": sca,
                "pc_ok": pc_ok, "sai_ok": sai_ok, "ipa_ok": ipa_ok,
            })

    return ISIRReport(
        total=passed + failed + skipped,
        passed=passed, failed=failed, skipped=skipped,
        failures=failures,
    )
