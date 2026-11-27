"""A drafted item holding more than one sentence is stored as the audit's own units (P196, after WHU-OT1-04c, which
stopped at draft: 9 stored page sentences were not units of the audit's splitter). $0, offline."""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
CASE = ROOT / "issues" / "WHU-OT1-04c-whu-lean-orch-t1-q1-04c"
SLUG = "whu-lean-orch-t1-q1-04c"


@pytest.fixture(autouse=True)
def _lean(monkeypatch):
    monkeypatch.setenv("WHU_LEAN", "1")


def test_two_sentences_become_two_units_and_e_g_stays_whole():
    import orchestrator as O
    two = ("The IPCC states with high confidence that net zero requires deep reductions in gross emissions. "
           "It also states that deploying CDR is unavoidable")
    assert O.draft_units(SLUG, two) == ["The IPCC states with high confidence that net zero requires deep reductions "
                                        "in gross emissions.", "It also states that deploying CDR is unavoidable"]
    one = "Compared with non-digital communication (e.g. pamphlets), it may have little effect & no harm"
    assert O.draft_units(SLUG, one) == [one]


def test_the_draft_step_stores_units_each_with_the_items_passages():
    src = (W / "orchestrator.py").read_text(encoding="utf-8")
    body = src[src.index("def code_draft"):src.index("def draft_units")]
    assert "for piece in draft_units(ctx.slug, x[\"text\"]):" in body
    assert body.index("provenance[t] = ") > body.index("for piece in draft_units")


def test_04c_recorded_draft_rebuilt_as_units_passes_the_standing_check():
    if not (CASE / "draft" / "page.json").exists():
        pytest.skip("04c records not present")
    import orchestrator as O
    from orch.page import Page
    doc = json.loads((CASE / "draft" / "page.json").read_text())
    page = Page(doc)
    before = O.splitter_mismatches(SLUG, page, page.render())
    assert len(before) == 9
    for b in doc["blocks"]:
        if b.get("tag") != "p":
            continue
        out = []
        for s in b["sentences"]:
            m = re.search(r"\s*(\[[\d,–\-\s]+\])\.?\s*$", s)
            text, mark = (s[:m.start()], m.group(1)) if m else (s, "")
            nums = [int(n) for n in re.findall(r"\d+", mark)]
            body = text if text.endswith((".", "?", "!")) or not s.rstrip().endswith(".") else text + "."
            out += [O._with_marker(u, nums) for u in O.draft_units(SLUG, body)]
        b["sentences"] = out
    page = Page(doc)
    assert O.splitter_mismatches(SLUG, page, page.render()) == []
