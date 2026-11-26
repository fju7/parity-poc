"""Who holds the belief: a page claim must rest on a verified outlet (advisor's ruling 3b on P140, 2026-11-26).

The belief step (orch/premise_reading.belief_outlets) proposes published outlets and code verifies each. When none
verifies, the run no longer STOPs: premise.json records `belief.outlet_unverified`, the page makes no claim about
where or by whom the belief is held, and it says UNVERIFIED (a generated sentence, lean_sentences). This module is
the preflight row that holds that line:

  * a page sentence that ASSERTS WHO HOLDS the belief (HOLDER below: "widely believed", "many people think",
    "campaigners argue", "it is often said", "the conventional wisdom", ...) must name one of the verified outlets
    (premise.json belief.carried_by), else STOP;
  * with no verified outlet, every such sentence STOPs, and UNVERIFIED must be on the page.

The patterns are a fail-closed net for the sentences a drafter writes about holders; a sentence they do not catch is
read by the audit as any other sentence.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROW = "belief claims rest on a verified outlet"
UNVERIFIED = "We could not verify where this belief is published."

# Who might be said to hold a belief. Not "many / most / some", nor researchers, scientists, experts or authors:
# "most studies say", "the authors argue" report the evidence, which the audit reads against its source.
_HOLDERS = (r"people|readers|parents|campaigners|advocates|activists|critics|commentators|policymakers|"
            r"politicians|governments|donors|ngos|charities|the public|the media|journalists|companies|polluters")
HOLDER = re.compile(
    r"\b(?:widely|commonly|often|generally|popularly|frequently|usually|broadly)\s+(?:believed|held|assumed|thought|"
    r"said|claimed|argued|accepted|reported|repeated|cited)\b"
    r"|\b(?:it\s+is|it's)\s+(?:often|commonly|widely|generally|frequently|sometimes)?\s*(?:said|claimed|argued|"
    r"assumed|believed|thought)\b"
    r"|\b(?:common|popular|widespread|prevailing|received|conventional)\s+(?:belief|view|assumption|wisdom|"
    r"narrative|claim|idea|perception|understanding)\b"
    r"|\b(?:%s)\s+(?:\w+\s+){0,2}(?:believe|believes|think|thinks|assume|assumes|say|says|claim|claims|argue|"
    r"argues|hold|holds|insist|insists|maintain|maintains)\b" % _HOLDERS,
    re.I)


def holder_sentences(sentences: list[str]) -> list[str]:
    return [s for s in sentences if HOLDER.search(s or "") and s.strip() != UNVERIFIED]


def verified_outlets(premise: dict) -> list[str]:
    return [str(c.get("outlet") or "").strip() for c in ((premise.get("belief") or {}).get("carried_by") or [])
            if str(c.get("outlet") or "").strip()]


def check(sentences: list[str], premise: dict) -> tuple[bool, str]:
    """(ok, detail) for the page's SENTENCES against the premise record."""
    outlets = verified_outlets(premise)
    holders = holder_sentences(sentences)
    names = [o.lower() for o in outlets]
    bare = [s for s in holders if not any(n and n in s.lower() for n in names)]
    if bare:
        return False, ("%d sentence(s) assert who holds the belief without naming a verified outlet (%s): %s"
                       % (len(bare), ", ".join(outlets) if outlets else "none verified",
                          " || ".join(s[:140] for s in bare[:4])))
    unverified = (premise.get("belief") or {}).get("outlet_unverified")
    if not outlets and unverified:
        if not any(s.strip() == UNVERIFIED for s in sentences):
            return False, "no outlet verified and the page does not say %r" % UNVERIFIED
        return True, "no outlet verified: the page says %r and no sentence claims who holds the belief" % UNVERIFIED
    if not outlets:
        return True, "no outlet verified and no sentence claims who holds the belief"
    return True, "%d sentence(s) about who holds the belief, each naming a verified outlet (%s)" % (
        len(holders), ", ".join(outlets))


def preflight_rows(slug: str, page, OK: str, BAD: str) -> list[tuple[str, str, str]]:
    """PAGE: the page's path, or its HTML."""
    import source_ledger as L
    import source_store as store
    if isinstance(page, Path) or (isinstance(page, str) and "<" not in page and Path(page).exists()):
        page_html = Path(page).read_text(encoding="utf-8") if Path(page).exists() else ""
    else:
        page_html = page or ""
    case = store.case_dir(slug)
    if case is None:
        return []
    try:
        premise = json.loads((Path(case) / "premise.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return [(ROW, BAD, "no premise.json")]
    ok, detail = check(L.sentences(L.plain(page_html)), premise)
    return [(ROW, OK if ok else BAD, detail)]
