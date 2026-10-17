"""B19, B20, B21: a sentence may not be surer than what it rests on.

A three-judge read of the 80 judgement sentences in the four WHU test issues
found every confirmed reasoning error leaning one way -- toward more certainty
than the cited source allows -- and 14 sentences about our own holdings cited
as though a document supported them. The fixtures below are those sentences,
copied verbatim from issues/WHU-T0n-ctp-*/bindings.json. Nothing here reads
the test issues; nothing here loads publish.py.

  B19  T01 s85  premise "should be interpreted cautiously"; sentence "does not
                support" -- the caution became a verdict.             -> WARN
  B20  T04 s60  "high" against a premise "with moderate certainty".   -> STOP
       T03 s53  "moderate to good"; its premise spans state NO grade (the
                Cochrane review's "low-certainty" is in the document, not in
                the span cited) -- so the ceiling cannot be read.     -> WARN
       T01 s82  "reasonably high"; same: no premise states a grade.   -> WARN
  B21  T01 s17  "We hold the abstract of this review" cites S003.     -> STOP,
                and is handed to epistemic.check_sentence.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

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
SLUG = "testissue"

T01_S85 = {
    "sentence": "The evidence does not support choosing between those three on "
                "the basis of age or sex.",
    "bucket": "judgement", "on_page": True,
    "premises": [{"source_id": "S001", "span": "confounding means our moderators "
                  "for age and sex should be interpreted cautiously"}],
    "step": "The age and sex moderators are study-level and possibly confounded, "
            "as discussed above."}
T04_S60 = {
    "sentence": "Confidence in direction is high that routine supplements do not "
                "prevent fractures or falls in healthy older adults living at home "
                "who are not deficient.",
    "bucket": "judgement", "on_page": True,
    "premises": [
        {"source_id": "S001", "span": "hazard ratio, 0.98; 95% confidence interval "
                                      "[CI], 0.89 to 1.08"},
        {"source_id": "S002", "span": "Vitamin D had no effect on falling in the "
                                      "past month"},
        {"source_id": "S010", "span": "The USPSTF concludes with moderate certainty "
                                      "that supplementation with vitamin D with or "
                                      "without calcium has no net benefit"}],
    "step": "Two mega-trials and a pooled review agree; the Task Force grades its "
            "conclusion moderate certainty, which bounds 'high' to direction rather "
            "than to an exact zero."}
T03_S53 = {
    "sentence": "Confidence that intermittent fasting works about as well as calorie "
                "restriction is moderate to good: reviews, a year-long time-restricted "
                "trial and a year-long alternate-day trial agree.",
    "bucket": "judgement", "on_page": True,
    "premises": [
        {"source_id": "S001", "span": "Compared to regular dietary advice, "
         "intermittent fasting may result in little to no difference in percentage "
         "from baseline weight loss"},
        {"source_id": "S005", "span": "Alternate-day fasting did not produce superior "
                                      "adherence, weight loss"},
        {"source_id": "S004", "span": "Changes in weight were not significantly "
                                      "different in the two groups at the 12-month "
                                      "assessment"}],
    "step": "Independent designs converge on no meaningful average difference."}
T01_S82 = {
    "sentence": "Confidence in direction is reasonably high: exercise helps depressive "
                "symptoms, across several independent syntheses and across trials "
                "judged at low risk of bias.",
    "bucket": "judgement", "on_page": True,
    "premises": [
        {"source_id": "S003", "span": "the pooled SMD was smaller (SMD -0.46, 95% CI "
                                      "-0.88 to -0.04)"},
        {"source_id": "S004", "span": "moderate effects when analyses were restricted "
         "to low risk of bias studies (SMD=-0.666, 95% CI -0.99 to -0.34, k=12"},
        {"source_id": "S001", "span": "Exercise is an effective treatment for "
                                      "depression"}],
    "step": "Restricting to lower-bias trials in two separate reviews still yields "
            "intervals excluding zero; the BMJ network concurs."}
T01_S17 = {
    "sentence": "We hold the abstract of this review, not the full text, so we cannot "
                "check its tables or its trial-by-trial judgements.",
    "bucket": "judgement", "on_page": True,
    "premises": [{"source_id": "S003", "span": "Subscription required"}],
    "step": "The bibliographic record we hold lists the full text as "
            "subscription-only; sources.json records S003 as abstract_held."}


class _Epistemic:
    """Stands in for epistemic.py; records every sentence it is asked about."""
    PASS, FAIL, NOT_EVALUATED = "PASS", "FAIL", "NOT EVALUATED"

    def __init__(self, verdict="PASS"):
        self.asked = []
        self.verdict = verdict

    def check_sentence(self, sentence, slug):
        self.asked.append((sentence, slug))
        return [{"verdict": self.verdict, "asserted": "HOLD", "source": "S003",
                 "recorded": "abstract_held", "why": "stub"}]


@pytest.fixture
def store_check(monkeypatch):
    stub = _Epistemic()
    monkeypatch.setitem(sys.modules, "epistemic", stub)
    return stub


def verdicts(row, slug=SLUG):
    return [(f["check"], f["verdict"]) for f in B.calibration_findings(dict(row), slug)]


def severity(row):
    return {B.CALIBRATION_SEVERITY[v] for _, v in verdicts(row)}


# --- B19 ------------------------------------------------------------------

def test_t01_s85_negating_a_cautious_premise_warns(store_check):
    found = B.b19_hedge_dropped(dict(T01_S85))
    assert [f["verdict"] for f in found] == ["evidence hedge dropped"]
    assert found[0]["hedge"] == "cautiously"
    assert "does not support" in found[0]["why"]
    assert B.CALIBRATION_SEVERITY["evidence hedge dropped"] == B.WARN


def test_a_sentence_that_keeps_the_hedge_is_not_reported():
    row = dict(T01_S85, sentence="The evidence on age and sex is too few studies "
                                 "deep to choose between those three.")
    assert B.b19_hedge_dropped(row) == []


def test_negation_cancels_a_hedge_word_in_the_same_sentence():
    """'does not support' counts as no hedge even beside one of the words."""
    row = dict(T01_S85, sentence="The evidence does not support choosing between "
                                 "those three, given limited moderator data.")
    assert [f["verdict"] for f in B.b19_hedge_dropped(row)] == ["evidence hedge dropped"]


def test_hedges_are_whole_words():
    row = dict(T01_S85, premises=[{"source_id": "S001",
                                   "span": "Mayo enrolled maybe-later cohorts"}])
    assert B.b19_hedge_dropped(row) == []


def test_a_bound_sentence_is_measured_against_its_span_and_also_rests_on():
    row = {"sentence": "Exercise reduces depressive symptoms.", "bucket": "context",
           "source_id": "S003", "span": "Exercise reduced symptoms.",
           "also_rests_on": [{"source_id": "S003", "span": "low certainty evidence"}],
           # a premise on a non-judgement row is not what the sentence rests on
           "premises": [{"source_id": "S009", "span": "this may be so"}]}
    found = B.b19_hedge_dropped(row)
    assert found and found[0]["hedge"] == "low certainty"
    assert "S009" not in found[0]["why"]


# --- B20 ------------------------------------------------------------------

def test_t04_s60_high_above_a_moderate_grade_stops(store_check):
    found = B.b20_confidence_ceiling(dict(T04_S60))
    assert [f["verdict"] for f in found] == ["confidence above its cited grade"]
    assert "moderate (S010)" in found[0]["why"]
    assert B.CALIBRATION_SEVERITY[found[0]["verdict"]] == B.BAD


def test_the_95_percent_confidence_interval_is_not_a_grade():
    assert B.stated_grades(T04_S60["premises"][0]["span"]) == []


def test_t03_s53_states_no_grade_so_it_warns_not_stops(store_check):
    """The brief expected STOP. The premise spans state no grade, so by the
    rule as written the ceiling cannot be read: reported, not passed."""
    found = B.b20_confidence_ceiling(dict(T03_S53))
    assert [f["verdict"] for f in found] == ["confidence stated without a cited grade"]
    assert found[0]["level"] == "moderate to good"
    assert B.CALIBRATION_SEVERITY[found[0]["verdict"]] == B.WARN


def test_t03_s53_stops_once_the_cochrane_grade_is_in_a_premise():
    row = dict(T03_S53, premises=T03_S53["premises"] + [
        {"source_id": "S001", "span": "little to no difference in weight loss "
                                      "(low-certainty evidence)"}])
    assert [f["verdict"] for f in B.b20_confidence_ceiling(row)] == \
        ["confidence above its cited grade"]


def test_t01_s82_reasonably_high_with_no_cited_grade_warns(store_check):
    found = B.b20_confidence_ceiling(dict(T01_S82))
    assert [f["verdict"] for f in found] == ["confidence stated without a cited grade"]
    assert found[0]["level"] == "reasonably high"


def test_low_risk_of_bias_is_not_a_grade():
    assert B.stated_grades(T01_S82["premises"][1]["span"]) == []


def test_grade_departure_lifts_the_stop_and_nothing_else_does():
    assert B.b20_confidence_ceiling(dict(T04_S60, step="a long careful step",
                                         falsifier="x")) != []
    assert B.b20_confidence_ceiling(dict(T04_S60, grade_departure="   ")) != []
    row = dict(T04_S60, grade_departure="Direction, not size: two trials of 25,871 "
                                        "and 21,315 agree in sign.")
    assert B.b20_confidence_ceiling(row) == []


def test_level_at_or_below_the_grade_passes():
    row = dict(T04_S60, sentence="Confidence in direction is moderate that routine "
                                 "supplements do not prevent fractures.")
    assert B.b20_confidence_ceiling(row) == []


def test_very_low_is_read_as_very_low():
    assert B.stated_grades("GRADE certainty was very low for cancer") == ["very low"]


def test_a_sentence_not_about_confidence_is_not_examined():
    row = dict(T04_S60, sentence="The trials found high adherence.")
    assert B.b20_confidence_ceiling(row) == []


# --- B21 ------------------------------------------------------------------

def test_t01_s17_is_a_holdings_sentence_routed_to_the_store(store_check):
    got = verdicts(T01_S17)
    assert ("B21", "holdings sentence cites a document") in got
    assert store_check.asked == [(T01_S17["sentence"], SLUG)]
    assert B.BAD in severity(T01_S17)


def test_declared_to_the_store_with_no_document_is_not_a_stop(store_check):
    row = {k: v for k, v in T01_S17.items() if k != "premises"}
    row.update(bucket="deterministic", rests_on_store=["S003"])
    assert verdicts(row) == []
    assert store_check.asked == [(T01_S17["sentence"], SLUG)]


def test_the_store_disagreeing_stops(monkeypatch):
    monkeypatch.setitem(sys.modules, "epistemic", _Epistemic("FAIL"))
    row = {"sentence": T01_S17["sentence"], "bucket": "deterministic",
           "rests_on_store": ["S003"]}
    assert ("B21", "store disagrees") in verdicts(row)


def test_a_store_check_that_cannot_read_the_sentence_says_so(monkeypatch):
    stub = _Epistemic()
    stub.check_sentence = lambda s, slug: []
    monkeypatch.setitem(sys.modules, "epistemic", stub)
    row = {"sentence": "We have not opened that meta-analysis.",
           "bucket": "deterministic", "rests_on_store": ["S001"]}
    assert verdicts(row) == [("B21", "store check not evaluated")]


@pytest.mark.parametrize("sent", [
    "We hold two pieces of coverage, so this is a sample of what was carried, not "
    "a survey of it.",
    "We have not opened that study, so we report it only as cited.",
    "We did not obtain the DO-HEALTH investigators' own summary paper, of which the "
    "open repository holds only a stub.",
    "Our search for a final version was limited to the Task Force's own website, "
    "and on the two pages we fetched there, none appeared.",
    "The guideline's bibliographic record lists two published errata, which we "
    "have not opened.",
])
def test_holdings_sentences_from_the_test_issues(sent):
    assert B.is_holdings(sent)


@pytest.mark.parametrize("sent", [
    "Yes, exercise reduces the symptoms of depression, and the reviews we hold "
    "agree on the direction of that effect much more firmly than on its size.",
    "The coverage we hold was better than its headlines.",
    "If someone does take vitamin D, the evidence we hold argues against very "
    "large intermittent doses.",
    "It reads as a typographical error, and we have not checked the published "
    "version of record.",
])
def test_a_claim_about_the_world_that_mentions_our_holdings_is_not_one(sent):
    assert not B.is_holdings(sent)


def test_declaring_a_world_claim_to_the_store_is_reported(store_check):
    row = dict(T01_S85, rests_on_store=["S001"])
    assert ("B21", "declared to the store, not a holdings sentence") in verdicts(row)
    assert store_check.asked == []


# --- wiring: bindings.py check reaches rows it used to skip ----------------

def test_run_checks_writes_calibration_flags_on_judgement_rows(tmp_path, monkeypatch,
                                                               store_check):
    monkeypatch.setattr(B, "path", lambda slug: tmp_path / "bindings.json")
    B.save(SLUG, {"bindings": {"a": dict(T04_S60), "b": dict(T01_S85),
                               "c": dict(T01_S17)}})
    tally = B.run_checks(SLUG)
    rows = B.load(SLUG)["bindings"]
    assert [f["check"] for f in rows["a"]["check_flags"]] == ["B20"]
    assert [f["check"] for f in rows["b"]["check_flags"]] == ["B19"]
    assert "B21" in {f["check"] for f in rows["c"]["check_flags"]}
    assert store_check.asked == [(T01_S17["sentence"], SLUG)]
    assert tally["calibration_stop"] == 2      # s60 ceiling, s17 cites a document
    assert tally["calibration_warn"] >= 1


def test_the_check_command_fails_on_a_stop(tmp_path, monkeypatch, store_check):
    monkeypatch.setattr(B, "path", lambda slug: tmp_path / "bindings.json")
    B.save(SLUG, {"bindings": {"a": dict(T04_S60)}})
    monkeypatch.setattr(sys, "argv", ["bindings.py", SLUG, "check"])
    assert B.main() == 1
    B.save(SLUG, {"bindings": {"b": dict(T01_S85)}})
    assert B.main() == 0                       # a WARN alone does not fail it


def test_no_new_bucket_was_added():
    assert B.BUCKETS == ("deterministic", "context", "judgement", "figure")


def test_both_new_fields_are_in_the_spec():
    spec = (ROOT / "docs" / "whatholdsup-claim-bindings-spec.md").read_text()
    for field in ("rests_on_store", "grade_departure"):
        assert field in spec, "%s is not documented in the spec" % field
