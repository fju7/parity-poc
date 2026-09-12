"""sweep_registry.py -- the registry sweep and the `registry claims match the
registry` row. No network: every test works on a capture built by hand.

The row blocks on CONTRADICTION and never on age; the sweep never synthesises
an NCT; a diff names the field. Each of those is a test here because each is
the kind of promise that quietly stops being true.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"))
import sweep_registry as R  # noqa: E402


def _state(**over):
    s = {"briefTitle": "Study of X", "officialTitle": "A Trial of X",
         "overallStatus": "ACTIVE_NOT_RECRUITING", "statusVerifiedDate": "2026-02",
         "lastUpdatePostDate": "2025-09-24", "primaryCompletionDate": "2029-10-26",
         "primaryCompletionDateType": "ESTIMATED", "completionDate": "2030-01-01",
         "completionDateType": "ESTIMATED", "resultsFirstPostDate": None,
         "hasResults": False, "versionHolder": "2026-09-12",
         "outcomes": [{"title": "Overall Survival (OS)", "type": "SECONDARY",
                       "reportingStatus": "NOT_POSTED", "anticipatedPostingDate": "2026-11"}]}
    s.update(over)
    return s


# ---------------------------------------------------------------- selection

def test_the_nct_is_read_from_the_url_and_never_from_a_title():
    assert R.nct_in_url({"url": "https://clinicaltrials.gov/study/NCT05933577"}) == "NCT05933577"
    assert R.nct_in_url({"url": "https://clinicaltrials.gov/study/nct05933577"}) == "NCT05933577"
    assert R.nct_in_url({"url": "https://example.org/x", "title": "KEYNOTE-054 NCT02362594"}) is None
    assert R.nct_in_url({"url": "", "also_called": ["NCT02362594"]}) is None


# --------------------------------------------------------------------- diff

def test_a_diff_names_the_field_with_before_and_after():
    before, after = _state(), _state(overallStatus="COMPLETED", hasResults=True)
    after["outcomes"][0]["reportingStatus"] = "POSTED"
    d = {x["field"]: (x["before"], x["after"]) for x in R.diff(before, after)}
    assert d["overallStatus"] == ("ACTIVE_NOT_RECRUITING", "COMPLETED")
    assert d["hasResults"] == (False, True)
    assert d["outcome[SECONDARY: Overall Survival (OS)].reportingStatus"] == ("NOT_POSTED", "POSTED")
    assert "versionHolder" not in d, "the registry's snapshot date is not a record change"


def test_reordered_outcomes_are_not_a_change():
    a = _state(outcomes=[{"title": "A", "type": "PRIMARY", "reportingStatus": "POSTED",
                          "anticipatedPostingDate": None},
                         {"title": "B", "type": "SECONDARY", "reportingStatus": "NOT_POSTED",
                          "anticipatedPostingDate": "2030-01"}])
    b = _state(outcomes=list(reversed(a["outcomes"])))
    assert R.diff(a, b) == []


# ------------------------------------------------------------------- alarms

def test_every_alarm_condition_fires_and_the_baseline_is_silent():
    today = date(2026, 9, 12)
    before = _state()
    after = _state(overallStatus="COMPLETED", hasResults=True, lastUpdatePostDate="2026-09-10")
    after["outcomes"][0]["reportingStatus"] = "POSTED"
    al = "\n".join(R.alarms("S020", "NCT02362594", before, after, today))
    assert "left NOT_POSTED -> POSTED" in al           # (a)
    assert "hasResults false -> true" in al            # (c)
    assert "overallStatus ACTIVE_NOT_RECRUITING -> COMPLETED" in al   # (d)
    assert "lastUpdatePostDate 2025-09-24 -> 2026-09-10" in al        # (e)
    # (b) needs no baseline: 2026-11 is within 60 days of 12 September 2026
    first = R.alarms("S020", "NCT02362594", None, _state(), today)
    assert len(first) == 1 and "within 60 days" in first[0]
    # and a baseline run raises none of (a)/(c)/(d)/(e)
    assert all("within 60 days" in x for x in first)
    far = _state()
    far["outcomes"][0]["anticipatedPostingDate"] = "2033-10"
    assert R.alarms("S026", "NCT03553836", None, far, today) == []


# ---------------------------------------------------------------- the check

def test_not_posted_against_posted_is_a_contradiction():
    c = R.claims_in("Overall survival is NOT_POSTED, with an anticipated posting date of November 2026.")
    kinds = {x["kind"] for x in c}
    assert kinds == {"not_posted", "anticipated"}
    st = _state()
    assert all(R.contradictions(x, st) is None for x in c)
    st["outcomes"][0]["reportingStatus"] = "POSTED"
    why = [R.contradictions(x, st) for x in c if x["kind"] == "not_posted"][0]
    assert why and "NOT_POSTED" in why and "POSTED" in why


def test_an_anticipated_date_the_record_no_longer_carries_is_a_contradiction():
    c = [x for x in R.claims_in("Overall survival is NOT_POSTED, with an anticipated posting "
                                "date of November 2026.") if x["kind"] == "anticipated"][0]
    st = _state()
    st["outcomes"][0]["anticipatedPostingDate"] = "2027-05"
    assert "2026-11" in (R.contradictions(c, st) or "") and "2027-05" in R.contradictions(c, st)


def test_a_last_update_date_the_record_has_moved_past_is_a_contradiction():
    c = R.claims_in("The record was last updated 24 September 2025 and carries no posted results.")
    kinds = {x["kind"] for x in c}
    assert kinds == {"last_update", "no_results"}
    st = _state()
    assert all(R.contradictions(x, st) is None for x in c)
    st["lastUpdatePostDate"] = "2026-09-10"
    why = [R.contradictions(x, st) for x in c if x["kind"] == "last_update"][0]
    assert why and "moved past" in why
    st = _state(hasResults=True, resultsFirstPostDate="2026-09-01")
    why = [R.contradictions(x, st) for x in c if x["kind"] == "no_results"][0]
    assert why and "hasResults is true" in why


def test_an_outcome_the_record_does_not_name_is_not_a_contradiction():
    c = [x for x in R.claims_in("Progression-free survival is NOT_POSTED in the record.")
         if x["kind"] == "not_posted"][0]
    assert R.contradictions(c, _state()) is None


def test_the_row_never_blocks_on_a_missing_capture(tmp_path, monkeypatch):
    """Class 3: nothing has checked this yet. WARN, not BLOCKED."""
    monkeypatch.setattr(R.RF, "case_dir", lambda slug: tmp_path)
    (tmp_path / "sources.json").write_text('{"sources": []}', encoding="utf-8")
    rows = R.preflight_rows("x", "<p>Overall survival is NOT_POSTED (NCT00000001).</p>")
    assert rows[0][0] == R.ROW and rows[0][1] == R.WARN
    assert "not checked" in rows[0][2]


def test_the_row_blocks_on_contradiction_and_names_the_sentence(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(R.RF, "case_dir", lambda slug: tmp_path)
    (tmp_path / "sources.json").write_text(json.dumps({"sources": [
        {"id": "S1", "url": "https://clinicaltrials.gov/study/NCT02362594",
         "also_called": ["KEYNOTE-054"]}]}), encoding="utf-8")
    st = _state()
    st["outcomes"][0]["reportingStatus"] = "POSTED"
    (tmp_path / "sweeps.json").write_text(json.dumps({"registry": {
        "S1": {"nct": "NCT02362594", "state": st, "swept": "2026-09-12"}}}), encoding="utf-8")
    page = ("<p>Intro.</p><li>KEYNOTE-054 (NCT02362594) <span>Registry record. Overall "
            "survival is NOT_POSTED, with an anticipated posting date of November 2026."
            "</span></li><footer id=\"updates\"><p>Both records mark overall survival "
            "NOT_POSTED (NCT02362594).</p></footer>")
    rows = R.preflight_rows("x", page)
    assert rows[0][1] == R.BAD
    assert "Overall survival is NOT_POSTED" in rows[0][2]
    assert "Both records mark" not in rows[0][2], "the change log recounts; it is not checked"


# ------------------------------------------- multi-record sentences (12 Sept)

TWO_TRIALS = ("KEYNOTE-054 and KEYNOTE-716 are both pembrolizumab against placebo; each lists "
              "overall survival as a secondary endpoint, and each registry record marks that "
              "result NOT_POSTED with a posting date still ahead of it — November 2026 for "
              "KEYNOTE-054, October 2033 for KEYNOTE-716.")
ALIASES = {"KEYNOTE-054": "NCT02362594", "KEYNOTE-716": "NCT03553836"}


def _attributed(sentence):
    mentions = R.records_named(sentence, ALIASES)
    return [(c["kind"], c["words"], R.attribute(c, sentence, mentions))
            for c in R.claims_in(sentence)]


def test_a_date_is_bound_to_the_record_named_immediately_after_it():
    rows = {w: ncts for k, w, (ncts, _how) in _attributed(TWO_TRIALS) if k == "anticipated"}
    assert rows["November 2026 for KEYNOTE-054"] == ["NCT02362594"]
    assert rows["October 2033 for KEYNOTE-716"] == ["NCT03553836"]


def test_a_distributive_clause_binds_the_claim_to_every_record_it_covers():
    kinds = [(k, sorted(ncts), how) for k, _w, (ncts, how) in _attributed(TWO_TRIALS)
             if k == "not_posted"]
    assert kinds == [("not_posted", ["NCT02362594", "NCT03553836"], "the clause says each of them")]
    neither = ("neither of the two placebo-controlled trials whose registry records we hold — "
               "KEYNOTE-054 and KEYNOTE-716 — has posted an overall-survival result at all.")
    got = [(k, sorted(ncts)) for k, _w, (ncts, _h) in _attributed(neither)]
    assert got == [("not_posted", ["NCT02362594", "NCT03553836"])]


def test_a_clause_naming_one_record_binds_to_it():
    s = ("The nearest scheduled comparator readout is KEYNOTE-054’s overall-survival result, "
         "anticipated in its registry record for November 2026; KEYNOTE-716’s is anticipated "
         "for October 2033.")
    rows = {c[1]: c[2][0] for c in _attributed(s) if c[0] == "anticipated"}
    assert rows["anticipated in its registry record for November 2026"] == ["NCT02362594"]
    assert rows["anticipated for October 2033"] == ["NCT03553836"]


def test_a_claim_no_clause_can_bind_is_unattributed_and_not_checked():
    s = "For KEYNOTE-054 and KEYNOTE-716 the record was last updated 24 September 2025."
    (kind, _w, (ncts, how)), = _attributed(s)
    assert kind == "last_update" and ncts == [] and how.startswith("UNATTRIBUTED")


def test_only_the_wrong_half_of_a_two_record_sentence_is_named(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(R.RF, "case_dir", lambda slug: tmp_path)
    (tmp_path / "sources.json").write_text(json.dumps({"sources": [
        {"id": "S020", "url": "https://clinicaltrials.gov/study/NCT02362594", "also_called": ["KEYNOTE-054"]},
        {"id": "S026", "url": "https://clinicaltrials.gov/study/NCT03553836", "also_called": ["KEYNOTE-716"]}]}),
        encoding="utf-8")
    s054 = _state()
    s716 = _state()
    s716["outcomes"][0]["anticipatedPostingDate"] = "2034-10"     # the page says 2033-10
    (tmp_path / "sweeps.json").write_text(json.dumps({"registry": {
        "S020": {"nct": "NCT02362594", "state": s054, "swept": "2026-09-12"},
        "S026": {"nct": "NCT03553836", "state": s716, "swept": "2026-09-12"}}, "runs": []}),
        encoding="utf-8")
    rows = R.preflight_rows("x", "<p>%s</p>" % TWO_TRIALS)
    row = [r for r in rows if r[0] == R.ROW][0]
    assert row[1] == R.BAD
    assert "NCT03553836" in row[2] and "October 2033 for KEYNOTE-716" in row[2]
    assert "NCT02362594" not in row[2] and "November 2026" not in row[2].split("page:")[0]


def test_the_alarm_row_warns_and_never_blocks(tmp_path, monkeypatch):
    import json
    from datetime import date as _d
    monkeypatch.setattr(R.RF, "case_dir", lambda slug: tmp_path)
    monkeypatch.setattr(R, "date", type("D", (), {"today": staticmethod(lambda: _d(2026, 9, 12))}))
    (tmp_path / "sources.json").write_text(json.dumps({"sources": [
        {"id": "S020", "url": "https://clinicaltrials.gov/study/NCT02362594", "also_called": ["KEYNOTE-054"]}]}),
        encoding="utf-8")
    (tmp_path / "sweeps.json").write_text(json.dumps({"registry": {
        "S020": {"nct": "NCT02362594", "state": _state(), "swept": "2026-09-12"}},
        "runs": [{"on": "2026-09-12", "command": "registry",
                  "alarms": ["S020 NCT02362594: overallStatus ACTIVE_NOT_RECRUITING -> COMPLETED"]}]}),
        encoding="utf-8")
    rows = {r[0]: r for r in R.preflight_rows("x", "<p>nothing about a registry here</p>")}
    assert rows[R.ALARM_ROW][1] == R.WARN
    assert "KEYNOTE-054 (NCT02362594) — overall survival anticipated to post 2026-11, 50 days away" in rows[R.ALARM_ROW][2]
    assert "overallStatus ACTIVE_NOT_RECRUITING -> COMPLETED" in rows[R.ALARM_ROW][2]
    assert not any(r[1] == R.BAD for r in rows.values())


# --------------------------------------------------------- identity, three ways

def test_identity_is_three_way_and_a_code_name_is_inconclusive_not_a_disagreement():
    ours = {"id": "S019", "title": "MONALEESA-2 — ClinicalTrials.gov results posting. NCT01958021.",
            "also_called": ["MONALEESA-2", "NCT01958021"]}
    paloma = {"id": "S020", "title": "PALOMA-2 — ClinicalTrials.gov results posting.",
              "also_called": ["PALOMA-2"]}
    others = [(paloma, "NCT01740427")]
    lee = {"briefTitle": "Study of Efficacy and Safety of LEE011 in Postmenopausal Women",
           "officialTitle": "A Randomized Study of LEE011 With Letrozole"}
    assert R.identity(ours, lee, others)["titles"] == "inconclusive"
    named = {"briefTitle": "Study of LEE011 (MONALEESA-2)", "officialTitle": ""}
    assert R.identity(ours, named, others)["titles"] == "agree"
    wrong = {"briefTitle": "A Study of Palbociclib + Letrozole (PALOMA-2)", "officialTitle": ""}
    got = R.identity(ours, wrong, others)
    assert got["titles"] == "disagree" and "S020" in got["why"]
