"""The source advocate's quotations are checked when written (GAP-018).

Each quotation is checked against the held text of its source (reading order;
enclosing quote marks aside). A failing one gets ONE re-ask, for that
objection only; if it still fails the objection keeps the true note "the
quotation is not in the held text". Every check is logged raw.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
spec = importlib.util.spec_from_file_location("source_advocate_q_t", WHU / "source_advocate.py")
SA = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SA)

HELD = {"S1": "The trial randomised 20 adults. Energy intake was 508 kcal per day higher on the ultra-processed diet."}


def _briefs():
    return [{"source": "S1", "mode": "objections", "principal": "the authors", "objections": [
        {"claim_quoted": "a", "objection": "x", "source_says": '"Energy intake was 508 kcal per day higher"'},
        {"claim_quoted": "b", "objection": "y", "source_says": "intake rose by about 500 kcal"},
        {"claim_quoted": "c", "objection": "z", "source_says": "a passage the paper does not contain"}]},
        {"source": "S2", "mode": "questions", "objections": [{"question": "q", "source_says": "never checked"}]}]


def test_quotations_are_checked_and_a_failing_one_is_re_asked_once():
    asked, logged = [], []

    def ask(b, o, text):
        asked.append(o["claim_quoted"])
        return {"source_says": "The trial randomised 20 adults." if o["claim_quoted"] == "b"
                else "still not in it"}
    briefs = _briefs()
    SA.check_quotations("x", briefs, HELD, ask=ask, log=logged.append)
    o1, o2, o3 = briefs[0]["objections"]
    assert asked == ["b", "c"]                                          # one re-ask each, only the failing
    assert o1["quotation_check"] == {"in_held_text": True, "asked": 1}  # enclosing quote marks aside
    assert o2["quotation_check"]["in_held_text"] is True and o2["source_says"] == "The trial randomised 20 adults."
    assert o2["source_says_first"] == "intake rose by about 500 kcal"
    assert o3["quotation_check"] == {"in_held_text": False, "asked": 2, "note": SA.QUOTE_NOTE}
    assert o3["source_says"] == "a passage the paper does not contain"   # the advocate's words stay
    assert "quotation_check" not in briefs[1]["objections"][0]          # questions are a person's
    assert [r["result"] for r in logged] == ["in the held text", "in the held text after one re-ask", SA.QUOTE_NOTE]
    assert logged[2]["first"] == "a passage the paper does not contain" and logged[2]["re_ask"] == "still not in it"


def test_the_ruling_model_then_gets_a_true_note(tmp_path):
    import ruling as R
    briefs = _briefs()
    SA.check_quotations("x", briefs, HELD, ask=lambda b, o, t: {}, log=None)
    for o in briefs[0]["objections"]:
        assert R._in_held(o["source_says"], HELD["S1"]) is o["quotation_check"]["in_held_text"]


def test_the_quotation_log_is_never_committed():
    root = WHU.parents[2]
    for p in ("issues/WHU-003-deskilling/advocate/quote_checks.jsonl",
              "issues/WHU-P02-ultra-processed-foods/advocate/quote_checks.jsonl"):
        assert subprocess.run(["git", "-C", str(root), "check-ignore", "-q", "--no-index", p]).returncode == 0, p
