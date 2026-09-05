"""The benchmark must be honest before it is useful.

A benchmark is a measuring instrument, and a broken one is worse than none: it
produces a number that ends arguments. These tests hold the three properties
that decide whether the number means anything.

  1. EVERY SPAN IS REAL. A case whose evidence is not in the held bytes is
     testing the judge against a fiction. All spans were verified against the
     documents before cases.jsonl was written; this keeps them verified.

  2. THE PACKET DOES NOT CONTAIN THE ANSWER. `why`, `provenance` and `verdict`
     are the grading key. Handing a judge the reason a sentence is wrong and
     then asking whether it is wrong measures nothing at all, and it is the
     easiest mistake to make here.

  3. THE SET CANNOT BE GAMED BY BLOCKING EVERYTHING. There must be CLEAR cases,
     they must include the corrected forms of BLOCK cases, and they must include
     at least one correct universal negative and one span whose surface words
     invite the opposite reading.

The fourth test records the baseline. It is not a pass/fail bar — it is the
floor a semantic layer has to beat, written down so nobody has to re-derive it.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
CASES = ROOT / "backend" / "data" / "whatholdsup" / "benchmark" / "cases.jsonl"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, WHU / ("%s.py" % name))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(WHU))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


BM = _load("benchmark")
ROWS = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]

# Source ids that name a document in the melanoma library. The others are
# deliberate: SELF is a claim about our own pipeline, REGISTRY and PAPER are
# issue-two cases whose documents are not in this issue's library.
REAL = {"S001", "S002", "S004", "S007", "S009", "S010", "S013", "S014",
        "S020", "S021", "S022", "S025", "S026"}


def test_every_case_is_well_formed():
    ids = [r["id"] for r in ROWS]
    assert len(ids) == len(set(ids)), "duplicate case ids"
    for r in ROWS:
        assert r["verdict"] in ("CLEAR", "BLOCK"), r["id"]
        assert r["sentence"].strip(), r["id"]
        assert r["why"].strip(), "%s has no grading reason" % r["id"]
        assert r["provenance"].strip(), "%s does not say where it came from" % r["id"]


@pytest.mark.parametrize("row", [r for r in ROWS
                                 for e in r["evidence"] if e["source_id"] in REAL],
                         ids=lambda r: r["id"])
def test_every_span_is_in_the_document_it_names(row):
    """A case built on a span that is not in the bytes tests nothing."""
    SC = _load("spancheck")
    for e in row["evidence"]:
        if e["source_id"] not in REAL:
            continue
        got = SC.b2_present(e["span"], "melanoma", e["source_id"])[0]
        assert got is True, "%s: span not in %s: %r" % (row["id"], e["source_id"], e["span"][:70])


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r["id"])
def test_the_packet_never_leaks_the_answer(row):
    """The grading key must not reach the judge."""
    p = BM.packet(row)
    assert row["why"] not in p, "%s: the packet contains the reason it is wrong" % row["id"]
    assert row["provenance"] not in p, "%s: the packet contains its provenance" % row["id"]
    # The reply-format instruction names BOTH verdicts, which leaks nothing.
    # What would leak is a packet that names only the correct one, so the test
    # is symmetry, not absence. The first version of this asserted absence and
    # failed on the format string -- a test wrong about the code rather than
    # code wrong about the world, which is the failure this whole file exists
    # to make visible, so it is recorded here rather than quietly fixed.
    assert ("CLEAR" in p) == ("BLOCK" in p), (
        "%s: the packet names one verdict and not the other" % row["id"])


def test_the_set_cannot_be_gamed_by_blocking_everything():
    clear = [r for r in ROWS if r["verdict"] == "CLEAR"]
    assert len(clear) >= 4, "too few CLEAR cases; blocking everything would score well"
    # the corrected forms of two BLOCK cases must be present as CLEAR
    corrected = {r["id"] for r in clear}
    assert {"WHU-B-002", "WHU-B-004"} <= corrected, (
        "the fixes for WHU-B-001 and WHU-B-003 must be CLEAR cases, or a judge "
        "that blocks the whole neighbourhood goes uncaught")
    # a correct universal negative, so 'contains a negative' is not a shortcut
    assert any("neither" in r["sentence"].lower() for r in clear), (
        "no CLEAR case contains a scoped universal negative")


def test_a_judge_that_blocks_everything_records_zero_false_clears():
    """Which is why false clears are never read alone."""
    results = [(r, "BLOCK", "") for r in ROWS]
    s = BM.score(results)
    assert s["total"].get("false_clear", 0) == 0
    assert s["total"]["false_block"] == sum(1 for r in ROWS if r["verdict"] == "CLEAR")


def test_the_span_baseline_misses_most_of_the_real_errors():
    """THE FLOOR. Span verification, stated as a judge, on the errors that
    actually reached readers. A semantic layer that does not beat this is
    buying nothing. Recorded so the number does not have to be re-derived, and
    so it fails loudly if the case set changes underneath it."""
    results = [(r, *BM.span_baseline(r)) for r in ROWS]
    s = BM.score(results)
    blocks = sum(1 for r in ROWS if r["verdict"] == "BLOCK")
    assert s["total"]["false_clear"] == 10, s["total"]
    assert blocks == 18
    # it clears more than half of everything that went wrong
    assert s["total"]["false_clear"] / blocks > 0.55


def test_holdout_withholds_whole_families_not_single_cases():
    """The current architecture overfit by tuning each check to the one incident
    that prompted it. Holding out individual cases would repeat that."""
    fam = "WRONG_SUBJECT"
    kept = BM.load(holdout=[fam])
    assert all(r["family"] != fam for r in kept)
    assert len(kept) == len(ROWS) - sum(1 for r in ROWS if r["family"] == fam)
