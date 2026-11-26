"""The readers' list and its budget after the fresh Q1-01 (advisor's rulings 1, 3 and 4 on P157, 2026-11-26).

WHU-OT1-01b's preflight counted 44 declarations against a budget of 10. Ruling 1: an out-of-scope declaration that
names a specific scope.out element, with the scope written before the run's acquire began, is not counted. Ruling 3:
a unit is counted once whether coverage.json or omissions.json declares it. Ruling 4: a unit the page states is
never declared. Figures and texts are 01b's own.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import coverage_check as C  # noqa: E402

LIVED = "Health workers' and clients' acceptability and lived experience of the tools"
COST = "Cost-effectiveness and the technical feasibility of implementation (connectivity, interoperability, data privacy law)"
SCOPE = {"question": "In primary health care, does using mobile phones or tablets to keep track of the care each patient "
                     "gets, together with on-screen prompts that guide health workers, reminder messages sent to "
                     "patients, or both, improve the care people receive and their health?",
         "out": [{"what": COST, "why": "These are important for the decision but are separate questions."},
                 {"what": LIVED, "why": "That is a qualitative-evidence question, distinct from effectiveness."}]}
WRITTEN = "2026-11-26T21:00:27+00:00"          # 01b's premise.json scope.written_at


def _case(tmp_path, chain=True):
    c = tmp_path / "case"
    (c / "orchestrator").mkdir(parents=True)
    if chain:                                   # 01b's chain: confirm ended 21:02:12, then acquire ran
        rows = [{"step": "premise", "at": "2026-11-26T21:00:28+00:00"},
                {"step": "confirm", "at": "2026-11-26T21:02:12+00:00"},
                {"step": "acquire", "at": "2026-11-26T21:05:38+00:00"}]
        (c / "orchestrator" / "chain.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return c


def _d(key, state="out_of_scope", element="", text="x"):
    sid, rng = key.split("@")
    a, b = (int(x) for x in rng.split("-"))
    return {"key": key, "state": state, "source": sid, "at": [a, b], "element": element, "text": text}


# ---- ruling 1 ------------------------------------------------------------------------------------------------

def test_01bs_s004_lived_experience_units_are_exempt(tmp_path):
    c = _case(tmp_path)
    assert C.acquire_began(c) == "2026-11-26T21:02:12+00:00"
    for key, el in (("S004@4606-4802", LIVED), ("S004@4968-5052", COST)):
        assert C.budget_exempt(_d(key, element=el), SCOPE, c, WRITTEN)
    counted, exempt, _ = C.budget_count([_d("S004@4606-4802", element=LIVED)], SCOPE, c, WRITTEN)
    assert counted == [] and len(exempt) == 1


def test_a_scope_written_after_acquire_began_exempts_nothing(tmp_path):
    c = _case(tmp_path)
    assert not C.budget_exempt(_d("S004@4606-4802", element=LIVED), SCOPE, c, "2026-11-26T21:03:00+00:00")
    assert not C.budget_exempt(_d("S004@4606-4802", element=LIVED), SCOPE, _case(tmp_path / "b", chain=False), WRITTEN)


def test_not_material_and_question_words_still_count(tmp_path):
    c = _case(tmp_path)
    assert not C.budget_exempt(_d("S004@6975-7076", state="not_material", element=LIVED), SCOPE, c, WRITTEN)
    # 01b's S006 paper reminders name words of the QUESTION ("mobile phones or tablets"), not a scope.out entry
    assert not C.budget_exempt(_d("S006@6023-6301", element="mobile phones or tablets"), SCOPE, c, WRITTEN)
    counted, exempt, _ = C.budget_count([_d("S004@6975-7076", state="not_material")], SCOPE, c, WRITTEN)
    assert len(counted) == 1 and exempt == []


# ---- ruling 3 ------------------------------------------------------------------------------------------------

def test_01bs_three_units_are_counted_once():
    pairs = [("S004@4078-4285", "S004@4078-4285"), ("S004@5738-5909", "S004@5738-5909"),
             ("S006@6023-6301", "S006@6023-6300")]          # coverage.json's key, then omissions.json's
    decls = [_d(a) for a, _ in pairs] + [_d(b) for _, b in pairs] + [_d("S006@5671-6022")]
    counted, exempt, twice = C.budget_count(decls)
    assert [d["key"] for d in counted] == ["S004@4078-4285", "S004@5738-5909", "S006@6023-6301", "S006@5671-6022"]
    assert [d["key"] for d in twice] == ["S004@4078-4285", "S004@5738-5909", "S006@6023-6300"] and exempt == []


# ---- ruling 4 ------------------------------------------------------------------------------------------------

S006_ABSTRACT = ("Adding computer‐generated reminders delivered on paper to healthcare professionals to one or more "
                 "co‐interventions (multi‐component intervention) probably improves quality of care slightly "
                 "compared with the co‐intervention(s) without the reminder component (median improvement 4.0% "
                 "(IQR 3.0% to 6.0%); 11 studies (13 comparisons);")
S006_PAGE = ("The same review found that adding reminders to one or more other interventions \"probably improve slightly "
             "quality of care by 4.0% compared with the co‐intervention(s) without the reminder component (in 11 "
             "studies (13 comparisons), moderate‐certainty evidence)\" [6].")


def test_s006s_4_0_percent_finding_stated_on_the_page_is_not_declared():
    assert C.result_figures(S006_ABSTRACT) == ["4.0", "11", "13"]          # the IQR's 3.0 and 6.0 left out
    d = _d("S006@6302-6662", text=S006_ABSTRACT)
    assert C.stated_on_page(d, {}, {"S006": ["Other S006 sentence.", S006_PAGE]}) == S006_PAGE
    assert C.stated_on_page(d, {}, {"S004": [S006_PAGE]}) is None           # bound to another source: not it


def test_s004s_cost_of_messages_bound_on_the_page_is_not_declared():
    d = _d("S004@5308-5428", element=COST, text="The cost of messages could also be a problem")
    assert C.stated_on_page(d, {"S004": [[5308, 5428]]}, {}) == "an on-page binding of S004"
    assert C.stated_on_page(d, {"S004": [[100, 200]]}, {}) is None


def test_a_single_figure_or_a_code_line_is_never_matched_by_figures():
    assert C.stated_by_figures("about 11 studies", ["11 studies said so"]) is None
    assert C.stated_on_page(_d("S003@5592-5764", state=C.REMOVED), {"S003": [[5592, 5764]]}, {}) is None
