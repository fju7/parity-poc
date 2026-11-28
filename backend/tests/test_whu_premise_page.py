"""The premise page (Fred's decision of 2026-11-28, relayed; premise_page.py). Offline: no model call."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import premise_page as PP  # noqa: E402

HELD = "Intro. DACCS has not been deployed at scale and its biggest drawback is the cost. Other text follows here."
EV = [HELD.index("DACCS"), HELD.index(" Other")]
EVIDENCE = "One review finds DACCS has not been deployed at scale and is costly [1]."
OTHER = "Removal is needed to balance residual emissions [1]."
PREMISE = {"belief": {"statement": "Removal cannot replace cuts. Machines remove a trivial amount."},
           "kill_condition_tested": {"result": "killed", "by": "a model's reading", "evidence": {
               "source": "S001", "offsets": EV}}}


def test_the_premise_sentences_come_from_the_record():
    got = [g["sentence"] for g in PP.premise_sentences(PREMISE)]
    assert got == [PP.PREMISE_LEAD, "The belief we recorded: “Removal cannot replace cuts.”",
                   "The belief we recorded: “Machines remove a trivial amount.”", PP.CONCLUSION]
    assert PP.CONCLUSION == "The evidence we hold does not support this premise."
    assert "false" not in PP.CONCLUSION


def test_the_premise_sentences_are_generated_frames():
    import lean_sentences as LS
    for g in PP.premise_sentences(PREMISE):
        assert LS.is_framed(g["sentence"]) and LS._one_sentence(g["sentence"])


def test_generate_adds_them_only_on_a_premise_page():
    import lean_sentences as LS
    issue = {"question": "What part can removal play?"}
    off = [g["sentence"] for g in LS.generate(issue, [], premise=PREMISE)]
    on = [g["sentence"] for g in LS.generate(issue, [], premise=PREMISE, premise_page=True)]
    assert PP.CONCLUSION not in off and PP.CONCLUSION in on and on[0].startswith("The question is:")


def test_a_finding_left_off_by_the_premise_page_has_its_own_line():
    import coverage_check as C
    assert C._off_state(["premise_page:2026-11-28T10:00:00+00:00"]) == C.PREMISE_STATE
    assert C._off_state(["failsafe:overstatement:x:y"]) == C.REMOVED
    assert C._off_state(["premise_page:x", "failsafe:overstatement:x:y"]) == C.REMOVED
    assert C.PREMISE_STATE not in C.COUNTED and "gives no answer" in C.CODE_LINES[C.PREMISE_STATE]


def test_the_premise_blocks_never_leak_into_the_limits_block():
    src = (W / "orchestrator.py").read_text(encoding="utf-8")
    body = src[src.index("def _generated_blocks"):src.index("def _source_list")]
    assert "PP.LEADS" in body


def test_premise_survived_passes_only_on_a_premise_page():
    src = (W / "premise.py").read_text(encoding="utf-8")
    i = src.index('if tested and t.get("result") == "killed":')
    assert "PP.marked(case_dir(slug)) is not None" in src[i:i + 400]


@pytest.fixture
def case(tmp_path, monkeypatch):
    import bindings as B
    import premise as PM
    import ruling as R
    import source_store as store
    c = tmp_path / "WHU-OT1-99-whu-x"
    (c / "draft").mkdir(parents=True)
    (c / "rulings").mkdir()
    monkeypatch.setattr(store, "case_dir", lambda slug: c)
    monkeypatch.setattr(PM, "load", lambda slug: PREMISE)
    monkeypatch.setattr(R, "held_texts", lambda slug: {"S001": HELD})
    rows = {"a": {"sentence": EVIDENCE, "source_id": "S001", "on_page": True,
                  "span": "DACCS has not been deployed at scale and its biggest drawback is the cost."},
            "b": {"sentence": OTHER, "source_id": "S001", "on_page": False, "off_page_by": "premise_page:t",
                  "span": "Intro."}}
    monkeypatch.setattr(B, "load", lambda slug: {"bindings": rows})
    from orch.page import fingerprint
    (c / PP.RECORD).write_text(json.dumps({"kept": {fingerprint(EVIDENCE): "kill_condition_tested"}}))
    (c / "draft" / "page.json").write_text(json.dumps({"kind": "premise_page", "blocks": [
        {"tag": "h2", "section": "instead", "text": PP.HEADINGS[1]},
        {"tag": "p", "section": "instead", "sentences": [EVIDENCE]}]}))
    (c / "rulings" / "overstatement.jsonl").write_text(json.dumps(
        {"sentence": EVIDENCE, "sentence_sha": fingerprint(EVIDENCE), "verdict": "no"}) + "\n")
    page = [g["sentence"] for g in PP.premise_sentences(PREMISE)] + [EVIDENCE]
    return c, page


def test_a_premise_page_whose_evidence_is_stated_and_checked_passes(case):
    c, page = case
    (row,) = PP.preflight_rows("whu-x", page)
    assert row[1] == PP.OK, row


def test_an_overstated_evidence_sentence_stops_it(case):
    c, page = case
    from orch.page import fingerprint
    (c / "rulings" / "overstatement.jsonl").write_text(json.dumps(
        {"sentence": EVIDENCE, "sentence_sha": fingerprint(EVIDENCE), "verdict": "yes"}) + "\n")
    (row,) = PP.preflight_rows("whu-x", page)
    assert row[1] == PP.BAD and "passed the overstatement check" in row[2]


def test_evidence_stated_by_no_sentence_stops_it(case):
    c, page = case
    (row,) = PP.preflight_rows("whu-x", [s for s in page if s != EVIDENCE])
    assert row[1] == PP.BAD and "stated by no sentence on the page" in row[2]


def test_a_sentence_not_kept_from_the_full_page_stops_it(case):
    c, page = case
    (c / "draft" / "page.json").write_text(json.dumps({"kind": "premise_page", "blocks": [
        {"tag": "p", "section": "instead", "sentences": [EVIDENCE, "The premise is false [1]."]}]}))
    (row,) = PP.preflight_rows("whu-x", page)
    assert row[1] == PP.BAD and "does not list as kept" in row[2]


def test_an_answer_section_or_a_missing_conclusion_stops_it(case):
    c, page = case
    (c / "draft" / "page.json").write_text(json.dumps({"kind": "premise_page", "blocks": [
        {"tag": "h2", "section": "answer", "text": "The short answer"}]}))
    (row,) = PP.preflight_rows("whu-x", [s for s in page if s != PP.CONCLUSION])
    assert row[1] == PP.BAD and "answer or verdict section" in row[2] and "not once" in row[2]


def test_a_full_page_has_no_premise_row(case):
    c, page = case
    (c / PP.RECORD).unlink()
    assert PP.preflight_rows("whu-x", page) == []


def test_not_killed_means_no_premise_page(case, monkeypatch):
    import premise as PM
    c, page = case
    monkeypatch.setattr(PM, "load", lambda slug: dict(PREMISE, kill_condition_tested={"result": "survived",
                                                                                      "by": "x"}))
    (row,) = PP.preflight_rows("whu-x", page)
    assert row[1] == PP.BAD and "cannot be a premise page" in row[2]
