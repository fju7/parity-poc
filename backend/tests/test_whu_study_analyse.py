"""Stage 1 analysis rules (scripts/analyse.py), on synthetic replies. Offline;
no real judge reply is read."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("analyse_t", ROOT / "study" / "whu-reliability" / "scripts" / "analyse.py")
A = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(A)


def _rep(label, judge_label=None, refused=False):
    return {"label": label, "judge_label": judge_label if judge_label is not None else
            (None if label in ("REFUSED", "INCOMPLETE_SOURCES") else label),
            "attempts": [{"refused": refused}]}


def test_the_refusal_rule_takes_the_other_judges_label():
    valid = A.M1_PASS | A.M1_FAIL | A.M1_EXCL
    raw = {"claude": _rep("REFUSED", refused=True), "openai": _rep("Absent")}
    assert A.per_judge_labels(raw, valid) == {"claude": "Absent", "openai": "Absent"}
    raw = {"claude": _rep("REFUSED", refused=True), "openai": _rep("REFUSED", refused=True)}
    assert A.per_judge_labels(raw, valid) == {"claude": None, "openai": None}


def test_scores_exclusions_and_agreement():
    assert A.score("Supported", A.M1_FAIL, A.M1_PASS) == 0.0
    assert A.score("UNCITED", A.M1_FAIL, A.M1_PASS) == 1.0
    for x in ("Unreachable", "INCOMPLETE_SOURCES", "NOT_VERIFIABLE_ABSTRACT", None):
        assert A.score(x, A.M1_FAIL, A.M1_PASS) is None
    r = {"uncited": False, "raw": {"claude": _rep("Supported"), "openai": _rep("Supported")}, "repeat": {}}
    assert A.agreed(r)
    assert not A.agreed(dict(r, repeat={"openai": _rep("Absent")}))       # a second read that changed
    assert not A.agreed(dict(r, raw={"claude": _rep("Supported"), "openai": _rep("Absent")}))


def _rows(whu_fail, claude_fail, n=10):
    rows = []
    for q in A.QUESTIONS:
        for s, k in (("WHU", whu_fail), ("Claude", claude_fail), ("ChatGPT", 5), ("Gemini", 5)):
            for i in range(n):
                lab = "Absent" if i < k else "Supported"
                rows.append({"item": "%s-%s-%d" % (q, s, i), "question": q, "system": s, "uncited": False,
                             "raw": {"claude": _rep(lab), "openai": _rep(lab)}, "repeat": {},
                             "labels": {"claude": lab, "openai": lab}})
    return rows


def test_the_decision_needs_half_and_an_interval_excluding_zero():
    v = A.view_scores(_rows(1, 6), A.M1_FAIL, A.M1_PASS)["combined"]
    out = A.analyse_view(v)
    assert out["systems"]["WHU"]["rate"] == 0.1 and out["systems"]["Claude"]["rate"] == 0.6
    assert out["vs_whu"]["Claude"]["holds"]
    out = A.analyse_view(A.view_scores(_rows(4, 6), A.M1_FAIL, A.M1_PASS)["combined"])
    assert not out["vs_whu"]["Claude"]["whu_at_most_half"] and not out["vs_whu"]["Claude"]["holds"]


def test_one_disagreement_scores_a_half_in_the_combined_view():
    r = {"item": "x", "question": "WHU-S01", "system": "WHU", "uncited": False, "repeat": {},
         "raw": {"claude": _rep("Supported"), "openai": _rep("Absent")}, "labels": {"claude": "Supported", "openai": "Absent"}}
    v = A.view_scores([r], A.M1_FAIL, A.M1_PASS)
    assert v["combined"][0][2] == 0.5 and v["agreed_only"][0][2] is None


def test_the_review_list_names_items_only_and_audits_a_fifth_of_agreed():
    rows = _rows(2, 2)
    rows[0]["raw"] = {"claude": _rep("Supported"), "openai": _rep("Absent")}
    lst = A.review_list(rows, "M1")
    assert all(set(x) == {"item", "measure", "reasons"} for x in lst)
    assert sum("judges disagree" in x["reasons"] for x in lst) == 1
    audit = [x for x in lst if x["reasons"] == ["random 20% audit of agreed items"]]
    assert len(audit) == 8 + 8 + 8 + 8 and audit == [x for x in A.review_list(rows, "M1")
                                                      if x["reasons"] == ["random 20% audit of agreed items"]]


def test_no_source_held_and_undelivered_are_named_apart_from_unreachable():
    rows = _rows(2, 2)
    rows[0]["raw"] = {}
    inc = lambda **k: {**_rep("INCOMPLETE_SOURCES"), "unreachable_sources": [], "undelivered_sources": [], **k}
    rows[1]["raw"] = {j: inc(undelivered_sources=[{"source_id": "S1"}]) for j in A.JUDGES}
    rows[2]["raw"] = {j: inc(unreachable_sources=[{"url": None}]) for j in A.JUDGES}
    assert [A.undelivered(r) for r in rows[1:3]] == [True, False]
    why = {x["item"]: x["reasons"] for x in A.review_list(rows, "M1")}
    assert why[rows[0]["item"]] == ["no cited source held (not sent to a judge)"]
    assert why[rows[1]["item"]] == ["source held but not delivered whole (INCOMPLETE_SOURCES)"]
    assert why[rows[2]["item"]] == ["source not held (INCOMPLETE_SOURCES)"]
