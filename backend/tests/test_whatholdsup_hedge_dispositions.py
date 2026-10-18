"""B19 dispositions: a person may dispose of a hedge word on a binding row.

Adopted 2026-10-18. Deskilling's 5850f3bd rests on S005's "they appear in
about 36% of the included studies", where 'appear' means 'occur' -- a count,
not a hedge -- and B19 reported it as a dropped hedge. The row may now carry
`hedge_dispositions`: [{word, why, by, on}], the same discipline as B6's
scope_words and B20's grade_departure. A matching, signed entry turns that
word's flag into INFO with the reason shown; anything less leaves it WARN.

Fixtures only. Nothing here reads an issue directory or loads publish.py.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, WHU / ("%s.py" % name))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(WHU))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


B = _load("bindings")

# 5850f3bd's S005 span, verbatim, and a sentence that states the count plainly.
SPAN = ("Effect sizes greater than 1 are rare in educational research (Kraft, "
        "2023), yet in Wang and Fan's meta-analysis, they appear in about 36% of "
        "the included studies.")
ROW = {"sentence": "Effect sizes above 1 were in about 36% of included studies.",
       "bucket": "context", "on_page": True, "source_id": "S005", "span": SPAN}
REASON = "S005's 'appear' means 'occur'; it states the 36% as a count, not a hedge."


def row(**extra):
    r = dict(ROW)
    r.update(extra)
    return r


def entry(word="appear", why=REASON, by="Fred Ugast", on="2026-10-18"):
    return {"word": word, "why": why, "by": by, "on": on}


def b19(r):
    return [f for f in B.calibration_findings(dict(r), "testissue") if f["check"] == "B19"]


def test_without_a_disposition_the_flag_is_warn():
    found = b19(row())
    assert [f["verdict"] for f in found] == ["evidence hedge dropped"]
    assert B.CALIBRATION_SEVERITY[found[0]["verdict"]] == B.WARN


def test_a_matching_signed_entry_makes_it_info_with_the_reason():
    found = b19(row(hedge_dispositions=[entry()]))
    assert [f["verdict"] for f in found] == ["evidence hedge disposed"]
    assert B.CALIBRATION_SEVERITY["evidence hedge disposed"] == B.INFO
    why = found[0]["why"]
    assert REASON in why and "Fred Ugast" in why and "2026-10-18" in why
    assert "'appear'" in why and found[0]["hedge"] == "appear"


def test_a_non_matching_word_stays_warn():
    found = b19(row(hedge_dispositions=[entry(word="may")]))
    assert [f["verdict"] for f in found] == ["evidence hedge dropped"]


def test_a_blank_why_or_by_is_ignored_and_stays_warn():
    for bad in (entry(why=""), entry(why="   "), entry(by=""), entry(by=None)):
        found = b19(row(hedge_dispositions=[bad]))
        assert [f["verdict"] for f in found] == ["evidence hedge dropped"], bad


def test_word_matching_ignores_case_and_spacing():
    found = b19(row(hedge_dispositions=[entry(word=" Appear ")]))
    assert [f["verdict"] for f in found] == ["evidence hedge disposed"]


def test_disposing_one_hedge_leaves_another_warn():
    span = SPAN + " These results may be biased."
    found = b19(row(span=span, hedge_dispositions=[entry()]))
    verdicts = sorted(f["verdict"] for f in found)
    assert verdicts == ["evidence hedge disposed", "evidence hedge dropped"]
    live = [f for f in found if f["verdict"] == "evidence hedge dropped"][0]
    assert live["hedge"] == "may" and "'appear'" not in live["why"]


def test_other_rows_are_unaffected():
    disposed, other = row(hedge_dispositions=[entry()]), row()
    assert [f["verdict"] for f in b19(disposed)] == ["evidence hedge disposed"]
    assert [f["verdict"] for f in b19(other)] == ["evidence hedge dropped"]
    assert "hedge_dispositions" not in other


def test_info_only_does_not_make_the_calibration_row_warn(monkeypatch, tmp_path):
    monkeypatch.setattr(B, "path", lambda slug: tmp_path / "bindings.json")
    monkeypatch.setattr(B.store, "sources", lambda slug: [])
    B.save("testissue", {"bindings": {"R00": dict(row(hedge_dispositions=[entry()]),
                                                  sentence_sha="R00",
                                                  check_flags=b19(row(hedge_dispositions=[entry()])))}})
    calib = [f for v in B.load("testissue")["bindings"].values()
             for f in v["check_flags"] if f["check"] in B.CALIBRATION_CHECKS]
    assert {B.CALIBRATION_SEVERITY[f["verdict"]] for f in calib} == {B.INFO}
