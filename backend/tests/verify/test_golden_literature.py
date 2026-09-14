"""Literature adapter acceptance, both directions (design doc §9).

Negative controls: the 381-source verify_sources snapshot of 2026-09-14. The
59 FABRICATED_IDENTIFIER and 33 WRONG_DOCUMENT verdicts must reproduce under
the shared HEADING test, source for source -- offline, from the snapshot's
recorded registry titles.

Positive controls: twelve real sources (4 DOI, 3 PMID, 1 PMCID, 4 NCT; five
open-access full texts, two abstract-only, four registry records), each read
by a person against the registry heading before it became a control. Every
one must resolve EXISTS, fetch the expected kind, and pass every applicable
binding kind. Replayed from tests/verify/fixtures/http, recorded live on
2026-09-14.

One negative control sits beside them: the PMID typed from memory while
assembling the set, which resolved to a lung-cancer trial and passed HEADING
until "advanced" and "cancer" stopped counting as distinctive.

Run: python3 -m pytest backend/tests/verify/test_golden_literature.py -q
"""
import json
import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("VERIFY_CACHE_DIR", str(Path(__file__).parent / "fixtures" / "http"))

from verify import http  # noqa: E402
http.CACHE_DIR = Path(os.environ["VERIFY_CACHE_DIR"])
from verify.bind import bind_all  # noqa: E402
from verify.literature import fetch, identify, resolve  # noqa: E402
from verify.text import agreement, LITERATURE_BOILERPLATE  # noqa: E402
from verify.types import Exists  # noqa: E402

SNAPSHOT = BACKEND / "scripts" / "signal" / "output" / "verify_sources_2026-09-14.json"
GOLDEN = json.loads((Path(__file__).parent / "golden_literature.json").read_text())


def _verdict(rec: dict) -> str:
    """verify_sources.check()'s verdict rule, with the shared HEADING test in place of its own."""
    if rec["exists"] == "NONEXISTENT":
        return "FABRICATED_IDENTIFIER"
    ratio = agreement(rec["title"], rec["registered_title"], LITERATURE_BOILERPLATE)[0] \
        if rec.get("registered_title") else None
    if ratio is not None and ratio <= 0.0:
        return "WRONG_DOCUMENT"
    if ratio is not None and ratio < 0.25 and rec["provenance"] != "MODEL_SUMMARY":
        return "TITLE_DIVERGENT"
    if rec["provenance"] == "MODEL_SUMMARY":
        return "NEVER_FETCHED"
    if rec["provenance"] == "EMPTY":
        return "NO_CONTENT"
    if rec["exists"] == "NO_IDENTIFIER":
        return "UNVERIFIABLE_URL"
    return "OK"


# Seven sources the 2026-09-14 run passed as NEVER_FETCHED that the shared
# HEADING test refuses as WRONG_DOCUMENT, because "cancer" and "advanced" no
# longer count as shared identity. Each was read on 2026-09-14 and is a
# different document -- the sixth is the EPIC alcohol paper resolving to a
# lipid-nanoparticle prostate study, the example in verify_sources.py's own
# docstring, which the old test let through on the word "cancer". Pinned by
# id so any further drift is visible, not absorbed.
NEWLY_REFUSED = {
    "761c3faa-f82f-4734-9c56-d52c1b502527",  # St Gallen International Expert Con -> Erdafitinib in BCG-treated high-risk non
    "7f9b39d8-4e2c-46b6-800f-bbb9d127f627",  # Soy Food Intake After Diagnosis of -> Randomized double-blind, placebo-control
    "f6d9c690-8356-4a69-a61a-8dc46ad96be8",  # Vitamin D and Marine Omega-3 Fatty -> Development and Validation of a Risk Pre
    "5963f33e-3663-4161-b80d-2d2128c076ae",  # Randomized Trial of a Mediterranea -> Intratumoral heterogeneity in gastric ca
    "6e95b6a8-0d99-4ff7-9721-683014c6b01e",  # Dietary Fiber Intake and Risk of B -> Induction cetuximab, paclitaxel, and car
    "a47bde6f-7dee-4cc1-b468-3c45df2ddb2d",  # Alcohol intake and breast cancer r -> Lipid nanoparticle siRNA systems for sil
    "0886aa32-7274-4d91-b796-c160a8f06652",  # WCRF/AICR Cancer Survivorship Diet -> American Cancer Society nutrition and ph
}


def test_the_381_snapshot_reproduces_source_for_source():
    snap = json.loads(SNAPSHOT.read_text())
    assert len(snap) == 381
    old_wrong = {r["id"] for r in snap if r["verdict"] == "WRONG_DOCUMENT"}
    old_fab = {r["id"] for r in snap if r["verdict"] == "FABRICATED_IDENTIFIER"}
    new_wrong = {r["id"] for r in snap if _verdict(r) == "WRONG_DOCUMENT"}
    new_fab = {r["id"] for r in snap if _verdict(r) == "FABRICATED_IDENTIFIER"}
    assert len(old_fab) == 59 and len(old_wrong) == 33
    assert new_fab == old_fab                                  # every fabricated identifier, still
    assert old_wrong <= new_wrong                              # every wrong document, still
    assert new_wrong - old_wrong == NEWLY_REFUSED              # and exactly these seven more
    others = [(r["id"], r["verdict"], _verdict(r)) for r in snap
              if _verdict(r) != r["verdict"] and r["id"] not in NEWLY_REFUSED]
    assert not others, others[:10]


@pytest.mark.parametrize("entry", GOLDEN["known_good"], ids=[e["id"] for e in GOLDEN["known_good"]])
def test_known_good_is_admitted(entry):
    ident = identify(entry["id"].split(":", 1)[1])
    res = resolve(ident)
    assert res.exists == Exists.EXISTS, res
    doc = fetch(res)
    assert doc is not None and doc.kind == entry["expect_kind"], (doc and (doc.kind, doc.route))
    ok, bindings = bind_all(entry["assertion"] or entry["ours"], res, doc, characterisation=entry["ours"])
    assert ok, [(b.kind.value, b.reason) for b in bindings if not b.ok]


@pytest.mark.parametrize("entry", GOLDEN["known_bad"], ids=[e["id"] for e in GOLDEN["known_bad"]])
def test_known_bad_is_refused_on_the_kind_it_should(entry):
    ident = identify(entry["id"].split(":", 1)[1])
    res = resolve(ident)
    doc = fetch(res)
    ok, bindings = bind_all(entry["assertion"], res, doc, characterisation=entry["ours"])
    assert not ok
    failed = {b.kind.value for b in bindings if not b.ok}
    assert entry["expect_fail_kind"] in failed, failed


def test_false_negative_rate_is_reported():
    """The number the design asks for: known-good refused / known-good."""
    refused = 0
    for entry in GOLDEN["known_good"]:
        ident = identify(entry["id"].split(":", 1)[1])
        res = resolve(ident); doc = fetch(res)
        ok, _ = bind_all(entry["assertion"] or entry["ours"], res, doc, characterisation=entry["ours"])
        refused += 0 if (ok and doc and doc.kind == entry["expect_kind"]) else 1
    print(f"\nliterature false-negative rate: {refused}/{len(GOLDEN['known_good'])}")
    assert refused == 0
