"""Fix 2, step 1: the advocate's objection types (post-study, 2026-10-27).

docs/whu-fix2-omission-rulings-design.md, section 1. No model is called: the
re-ask takes a fake `ask`, and the held-text check that decides whether its
answer is accepted is the real one (audit_stage.quoted_in / locate).
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))

import audit_stage as A          # noqa: E402
import source_advocate as SA     # noqa: E402

HELD = ("Section 1. Changes in layout could reduce emissions in developed countries (high confidence). "
        "Investment in public transport can further support a shift to less intensive modes (high confidence). "
        "Some changes could lead to induced demand (medium confidence).")
BOUND = ["Changes in layout could reduce emissions in developed countries"]
OMITTED = "Investment in public transport can further support a shift to less intensive modes"


def test_the_schema_asks_for_a_type_and_the_omitted_finding_itself():
    assert '"type":          "MISSTATES" | "LEAVES_OUT"' in SA.ADVOCATE_SYSTEM
    assert "never a passage the page already uses" in SA.ADVOCATE_SYSTEM
    assert "say\n   LEAVES_OUT and quote that finding" in SA.ADVOCATE_SYSTEM


def test_omission_kind_declared_suspected_default():
    assert SA.omission_kind({"type": "leaves_out"}) == (SA.LEAVES_OUT, "declared")
    assert SA.omission_kind({"type": "MISSTATES", "objection": "the page omits X"}) == (SA.MISSTATES, "declared")
    assert SA.omission_kind({"objection": "The page omits the second sentence."}) == (SA.LEAVES_OUT, "suspected")
    assert SA.omission_kind({"objection": "x", "why": "leaves out the transit finding"})[0] == SA.LEAVES_OUT
    assert SA.omission_kind({"objection": "The paper says reduced, not cut."}) == (SA.MISSTATES, "default")


def test_needs_reask_when_the_quotation_is_empty_or_already_on_the_page():
    o = {"type": "LEAVES_OUT", "source_says": ""}
    assert SA.needs_reask(o, HELD, BOUND)
    o["source_says"] = "Changes in layout could reduce emissions in developed countries (high confidence)."
    assert SA.needs_reask(o, HELD, BOUND)                         # overlaps a bound span
    o["source_says"] = OMITTED
    assert not SA.needs_reask(o, HELD, BOUND)                     # the omitted finding itself
    o["source_says"] = "A sentence the document does not contain."
    assert not SA.needs_reask(o, HELD, BOUND)                     # NOT_IN_SOURCE, decided later by code
    assert not SA.needs_reask({"type": "MISSTATES", "source_says": ""}, HELD, BOUND)


def _ask(reply):
    seen = []

    def ask(system, user):
        seen.append((system, json.loads(user)))
        return reply
    return ask, seen


def test_a_reask_answer_in_the_held_text_replaces_the_quotation():
    ask, seen = _ask({"source_says": OMITTED, "locator": "Section 1"})
    o = {"objection": "The page omits the transit finding.", "source_says": BOUND[0]}
    got = SA.reask_omission({"source": "S003", "principal": "the authors"}, o, HELD, BOUND, ask=ask)
    assert got["type"] == SA.LEAVES_OUT and got["source_says"] == OMITTED
    assert got["source_says_first"] == BOUND[0] and got["quotation_check"]["in_held_text"]
    assert seen[0][1]["already_on_the_page"] == BOUND
    assert "Do not\nparaphrase and do not search the web" in seen[0][0]


def test_a_reask_answer_not_in_the_held_text_is_refused_by_the_check_not_the_fake(monkeypatch):
    ask, _ = _ask({"source_says": "Public transport always cuts emissions by half."})
    o = {"objection": "omits it", "source_says": BOUND[0]}
    got = SA.reask_omission({"source": "S003"}, o, HELD, BOUND, ask=ask)
    assert got["source_says"] == BOUND[0] and "reask_note" in got
    # The refusal is the held-text check's: accept anything, and the same reply passes.
    monkeypatch.setattr(A, "quoted_in", lambda q, hay: True)
    assert "reask_note" not in SA.reask_omission({"source": "S003"}, o, HELD, BOUND, ask=ask)


def test_the_template_closes_an_omission_with_omission_and_did(tmp_path, monkeypatch):
    monkeypatch.setattr(SA.sl, "case_dir", lambda slug: tmp_path)
    briefs = [{"source": "S003", "title": "t", "principal": "p", "state": "full_text_held", "mode": "objections",
               "objections": [{"type": "LEAVES_OUT", "claim_quoted": "near", "objection": "omits X",
                               "source_says": OMITTED, "severity": "SERIOUS"},
                              {"type": "MISSTATES", "claim_quoted": "said", "objection": "wrong",
                               "source_says": BOUND[0], "severity": "MINOR"}]}]
    p = SA.write_template("x", "2026-10-27", briefs)
    chunks = p.read_text().split("### ")[1:]
    assert "**Type.** LEAVES_OUT" in chunks[0] and "**Nearest page sentence.** near" in chunks[0]
    assert "OMISSION: " in chunks[0] and "MERIT:" not in chunks[0]
    assert "MERIT:  " in chunks[1] and "OMISSION:" not in chunks[1]
    assert not SA._closed("### " + chunks[0], "objections")
    closed = chunks[0].replace("OMISSION: ", "OMISSION: out_of_scope — prescription").replace(
        "DID:      ", "DID:      nothing added")
    assert SA._closed("### " + closed, "objections")
    # A word outside the omission vocabulary does not close it, even with DID filled.
    assert not SA._closed("### " + closed.replace("OMISSION: out_of_scope", "OMISSION: maybe"), "objections")
