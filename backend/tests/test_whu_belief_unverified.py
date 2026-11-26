"""Advisor's ruling 3b on P140 (2026-11-26).

3b. When no outlet verifies, the run does not STOP: premise.json records belief.outlet_unverified, the two premise
    rows are warnings, the page says "We could not verify where this belief is published." (a generated sentence)
    and makes no claim about where or by whom the belief is held; any page sentence asserting who holds the belief
    must name a verified outlet (belief_claims, preflight row "belief claims rest on a verified outlet").
Nothing is fetched or spent: pages and replies are fakes, Q1-04's belief and refused outlets are its own records.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
Q104 = ROOT / "issues" / "WHU-OT1-04-whu-lean-orch-t1-q1-04"

import belief_claims as BC  # noqa: E402
import lean_sentences as LS  # noqa: E402
import premise as PM  # noqa: E402
from orch import premise_reading as P  # noqa: E402
from orch import steps as ST  # noqa: E402

BELIEF = json.loads((Q104 / "premise.json").read_text(encoding="utf-8"))["belief"]["statement"]
SHORT = b"<html><body><p>Direct air capture is expensive.</p></body></html>"


def _case(tmp_path):
    c = tmp_path / "issues" / "WHU-OT1-99-whu-x"
    c.mkdir(parents=True)
    (c / "premise.json").write_text(json.dumps({"belief": {"statement": BELIEF},
                                                "public_record_check": {"carried_in_general_coverage": ""}}))
    return c


def _get(url):
    if url.endswith("/robots.txt"):
        return {"status": 404, "headers": {}, "body": b"", "final_url": url}
    return {"status": 200, "headers": {}, "body": SHORT, "final_url": url}


def _asker():
    replies = [json.dumps({"outlets": [{"outlet": "Grist", "url": "https://grist.org/a", "sentence": "s"}]}),
               json.dumps({"outlets": [{"outlet": "Mongabay", "url": "https://news.mongabay.com/b", "sentence": "s"}]})]
    n = []

    def ask(prompt, max_tokens, role):
        n.append(role)
        return replies[len(n) - 1]
    return ask


def test_no_verified_outlet_is_recorded_and_the_premise_rows_do_not_stop(tmp_path, monkeypatch):
    c = _case(tmp_path)
    got = P.belief_outlets(c, _asker(), "m", get=_get)
    assert got["verified"] == 0
    d = json.loads((c / "premise.json").read_text())
    un = d["belief"]["outlet_unverified"]
    assert un["sentence"] == BC.UNVERIFIED and un["proposed"] == 2 and len(un["refused"]) == 2
    assert "carried_by" not in d["belief"]
    monkeypatch.setattr(PM, "load", lambda slug: d)
    monkeypatch.setattr(PM, "is_study", lambda slug: True)
    rows = {r[0]: r for r in PM.preflight_rows("x")}
    assert rows["belief shown to be held"][1] == PM.WARN and BC.UNVERIFIED in rows["belief shown to be held"][2]
    assert rows["carried in general coverage?"][1] == PM.WARN


def test_q1_04s_record_without_the_field_still_stops_as_before(monkeypatch):
    """Q1-04 ran before the field existed: its record has neither carried_by nor outlet_unverified, so its rows STOP
    as recorded (a run made before the rule is not re-read under it)."""
    d = json.loads((Q104 / "premise.json").read_text(encoding="utf-8"))
    assert not [c for c in d["belief"].get("carried_by") or [] if c.get("outlet")] and "outlet_unverified" not in d["belief"]
    monkeypatch.setattr(PM, "load", lambda slug: d)
    monkeypatch.setattr(PM, "is_study", lambda slug: True)
    rows = {r[0]: r for r in PM.preflight_rows("x")}
    assert rows["belief shown to be held"][1] == PM.BAD


def test_the_page_gets_the_generated_sentence_only_when_none_verified():
    un = {"belief": {"outlet_unverified": {"sentence": BC.UNVERIFIED}}}
    gen = LS.generate({"question": "Q?"}, [], premise=un)
    assert [g["sentence"] for g in gen if g["field"] == "premise.json belief.outlet_unverified"] == [BC.UNVERIFIED]
    assert LS.is_framed(BC.UNVERIFIED)
    ok = {"belief": {"carried_by": [{"outlet": "Grist"}], "outlet_unverified": {"sentence": BC.UNVERIFIED}}}
    assert not [g for g in LS.generate({"question": "Q?"}, [], premise=ok) if g["sentence"] == BC.UNVERIFIED]
    tmpl = {"belief": {"carried_by": [{"outlet": "", "url": ""}], "outlet_unverified": {"sentence": BC.UNVERIFIED}}}
    assert [g for g in LS.generate({"question": "Q?"}, [], premise=tmpl) if g["sentence"] == BC.UNVERIFIED]


@pytest.mark.parametrize("sentence", [
    "It is widely believed that planting trees does most of the work.",
    "Many people think removal machines will save us.",
    "Campaigners argue that carbon removal is a delay tactic.",
    "The conventional wisdom is that removal is a backstop."])
def test_a_sentence_saying_who_holds_the_belief_stops_without_a_verified_outlet(sentence):
    un = {"belief": {"outlet_unverified": {"sentence": BC.UNVERIFIED}}}
    ok, why = BC.check([sentence, BC.UNVERIFIED], un)
    assert not ok and "without naming a verified outlet" in why
    ver = {"belief": {"carried_by": [{"outlet": "Grist"}]}}
    assert not BC.check([sentence], ver)[0]                          # a verified outlet exists but is not named
    assert BC.check([sentence.rstrip(".") + ", as Grist reported."], ver)[0]


def test_with_none_verified_the_page_must_say_so():
    un = {"belief": {"outlet_unverified": {"sentence": BC.UNVERIFIED}}}
    assert BC.check(["The review found removal is small."], un) == (
        False, "no outlet verified and the page does not say %r" % BC.UNVERIFIED)
    assert BC.check(["The review found removal is small.", BC.UNVERIFIED], un)[0]


@pytest.mark.parametrize("sentence", [
    "Most studies say removal is costly.", "The review's authors argue for more trials.",
    "The IPCC assesses removal as necessary for net zero.", "We could not verify where this belief is published."])
def test_statements_about_the_evidence_are_not_holder_claims(sentence):
    assert BC.holder_sentences([sentence]) == []


def test_the_row_is_in_the_lean_preflight_and_fails_closed():
    src = (W / "publish.py").read_text(encoding="utf-8")
    i = src.index('_sibling("belief_claims").preflight_rows(slug, page, OK, BAD)')
    assert '"belief claims rest on a verified outlet", BAD, "did not run' in src[i:i + 400]
