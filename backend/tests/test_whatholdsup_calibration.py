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
                the span cited).                                      -> STOP
       T01 s82  "reasonably high"; same: no premise states a grade.   -> STOP
       T02 s75  "moderate"; no premise states a grade.                -> STOP
       T03 s54  "low", no grade: claims nothing a grade could undercut -> none
  B21  T01 s17  "We hold the abstract of this review" cites S003.     -> STOP,
                and is handed to epistemic.check_sentence, which takes a
                declared rests_on_store as the subject (round 2).
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
        self.declared = []
        self.verdict = verdict

    def check_sentence(self, sentence, slug, declared=None):
        self.asked.append((sentence, slug))
        self.declared.append(declared)
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


def test_negation_does_not_cancel_another_hedge_word_in_the_sentence():
    """Round 2: 'does not support' removes the hedge only when nothing else is one."""
    row = dict(T01_S85, sentence="The evidence does not support choosing between "
                                 "those three, given limited moderator data.")
    assert B.b19_hedge_dropped(row) == []


T02_S40 = {
    "sentence": "For breast, pancreatic and prostate cancer, among others, the review "
                "found limited evidence, graded as no evidence of association.",
    "bucket": "context", "on_page": True, "source_id": "S001",
    "span": "We found limited evidence for pooled analyses, including mixed cohort and "
            "case-control study designs, of the association between greater "
            "ultra-processed food exposure and higher risks of breast cancer",
    "also_rests_on": [{"source_id": "S001", "span": "pancreatic cancer (odds ratio 1.24, "
                       "0.85 to 1.79; class V; very low), and prostate cancer"}]}
T02_S68 = {
    "sentence": "Naming cancer first sits awkwardly with the paper, where cancer overall "
                "reached only the suggestive class at very low certainty and several "
                "specific cancers showed no evidence of association.",
    "bucket": "judgement", "on_page": True,
    "premises": [{"source_id": "S007", "span": "32 damaging health outcomes including cancer"},
                 {"source_id": "S001", "span": "higher risks of incident cancer overall "
                  "(hazard ratio 1.12, 1.06 to 1.19; class III; very low)"}]}


@pytest.mark.parametrize("row", [T02_S40, T02_S68], ids=["T02 s40", "T02 s68"])
def test_a_negating_sentence_that_keeps_its_hedge_is_not_reported(row):
    assert B.b19_hedge_dropped(dict(row)) == []


def test_t01_s85_still_warns_after_the_negation_fix():
    assert [f["verdict"] for f in B.b19_hedge_dropped(dict(T01_S85))] == \
        ["evidence hedge dropped"]


T04_S16 = {
    "sentence": "The D-Health trial in Australia gave 21,315 people aged 60 to 84 a "
                "monthly dose of 60,000 IU or a placebo for up to five years.",
    "bucket": "context", "on_page": True, "source_id": "S002",
    "span": "Between February 2014 and May 2015, 21 315 participants aged 60-84 years "
            "were randomized (1:1) to monthly doses of either 60 000 IU of "
            "colecalciferol or placebo for a maximum of 5 years."}


def test_t04_s16_may_the_month_is_not_a_hedge():
    assert B.b19_hedge_dropped(dict(T04_S16)) == []


@pytest.mark.parametrize("text", ["enrolled in May 2015", "on May 3 the panel met",
                                  "the end of May of that year", "posted 16 May 2024",
                                  "from 1st May onwards"])
def test_may_in_a_date_is_not_a_hedge(text):
    assert B._hedges(B._EVIDENCE_HEDGE, text) == []


@pytest.mark.parametrize("text", ["May be effective in some groups.",
                                  "Exercise may help.", "it may 2 or 3 times"])
def test_may_that_is_not_a_date_still_is(text):
    assert B._hedges(B._EVIDENCE_HEDGE, text) == ["may"]


@pytest.mark.parametrize("word", ["perhaps", "would tend to", "arguably"])
def test_the_added_hedges_are_in_both_lists(word):
    assert B._hedges(B._EVIDENCE_HEDGE, "this is %s so" % word) == [word]
    assert B.sentence_hedges("this is %s so" % word) == [word]


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


def test_t03_s53_states_no_grade_and_stops(store_check):
    """Round 2: a level above low with no cited grade is a STOP."""
    found = B.b20_confidence_ceiling(dict(T03_S53))
    assert [f["verdict"] for f in found] == ["confidence stated without a cited grade"]
    assert found[0]["level"] == "moderate to good"
    assert B.CALIBRATION_SEVERITY[found[0]["verdict"]] == B.BAD


T02_S75 = {
    "sentence": "Confidence in direction is moderate: two randomised trials and a large "
                "body of observational work point the same way for a diet dominated by "
                "ultra-processed food.",
    "bucket": "judgement", "on_page": True,
    "premises": [{"source_id": "S002", "span": "Energy intake was greater during the "
                  "ultra-processed diet (508±106 kcal/d; p=0.0001)"},
                 {"source_id": "S004", "span": "with significantly greater %WC on MPF"},
                 {"source_id": "S001", "span": "Overall, direct associations were found "
                  "between exposure to ultra-processed foods and 32 (71%) health "
                  "parameters"}]}
T03_S54 = {
    "sentence": "Confidence that any version is reliably better is low, and the "
                "advantage in the best trial for fasting was modest.",
    "bucket": "judgement", "on_page": True,
    "premises": [{"source_id": "S002", "span": "moderate-to-long-term trials (≥24 weeks, "
                  "n=17) only showed benefits in weight reduction in diet strategies "
                  "compared with ad-libitum"},
                 {"source_id": "S006", "span": "4:3 IMF produced modestly greater weight "
                                               "loss"}]}


def test_t02_s75_moderate_with_no_cited_grade_stops():
    found = B.b20_confidence_ceiling(dict(T02_S75))
    assert [(f["verdict"], f["level"]) for f in found] == \
        [("confidence stated without a cited grade", "moderate")]
    assert B.CALIBRATION_SEVERITY[found[0]["verdict"]] == B.BAD


def test_t03_s54_low_with_no_cited_grade_is_not_flagged():
    assert B.b20_confidence_ceiling(dict(T03_S54)) == []


def test_very_low_with_no_cited_grade_is_not_flagged():
    row = dict(T03_S54, sentence="Confidence in magnitude is very low.")
    assert B.b20_confidence_ceiling(row) == []


def test_grade_departure_does_not_lift_a_missing_grade():
    """Unchanged from round 1: the exception covers the ceiling only."""
    row = dict(T03_S53, grade_departure="Three designs agree.")
    assert [f["verdict"] for f in B.b20_confidence_ceiling(row)] == \
        ["confidence stated without a cited grade"]


def test_t03_s53_stops_once_the_cochrane_grade_is_in_a_premise():
    row = dict(T03_S53, premises=T03_S53["premises"] + [
        {"source_id": "S001", "span": "little to no difference in weight loss "
                                      "(low-certainty evidence)"}])
    assert [f["verdict"] for f in B.b20_confidence_ceiling(row)] == \
        ["confidence above its cited grade"]


def test_t01_s82_reasonably_high_with_no_cited_grade_stops(store_check):
    found = B.b20_confidence_ceiling(dict(T01_S82))
    assert [f["verdict"] for f in found] == ["confidence stated without a cited grade"]
    assert found[0]["level"] == "reasonably high"
    assert B.CALIBRATION_SEVERITY[found[0]["verdict"]] == B.BAD


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
    assert store_check.declared == [["S003"]]       # the row's subject is passed on


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


# --- epistemic.py, round 2: a declared subject, and three phrasings ---------

E = _load("epistemic")

SOURCES = [
    {"id": "S003", "document_class": "document", "access": {"state": "abstract_held"}},
    {"id": "S008", "document_class": "document", "access": {"state": "full_text_held"}},
    {"id": "S009", "document_class": "document", "access": {"state": "blocked"}},
    {"id": "S010", "access": {"state": "full_text_held"}},          # unclassified
]


@pytest.fixture
def es(monkeypatch):
    monkeypatch.setattr(E, "_sources", lambda slug: SOURCES)
    monkeypatch.setattr(E, "store_subjects", lambda s, slug: [])
    asked = []
    monkeypatch.setattr(E, "resolve", lambda s, slug: asked.append(s) or [])
    monkeypatch.setattr(E, "declared_sources", lambda s, slug: [])
    return asked


def test_a_declared_subject_is_checked_and_the_text_is_not_asked(es):
    got = E.check_sentence(T01_S17["sentence"], SLUG, declared=["S003"])
    assert [(v["verdict"], v["source"], v["recorded"]) for v in got] == \
        [("PASS", "S003", "abstract_held")]
    assert got[0]["why"] == "declared by rests_on_store"
    assert es == []                                  # resolve() never called


def test_a_declared_subject_the_store_contradicts_fails(es):
    got = E.check_sentence("We hold two pieces of coverage, so this is a sample.",
                           SLUG, declared=["S008", "S009"])
    assert [(v["verdict"], v["source"]) for v in got] == [("PASS", "S008"), ("FAIL", "S009")]


def test_a_declared_id_not_in_sources_is_not_evaluated(es):
    got = E.check_sentence("We hold the abstract of that trial.", SLUG, declared=["S099"])
    assert [(v["verdict"], v["source"]) for v in got] == [("NOT EVALUATED", "S099")]
    assert "not in sources.json" in got[0]["why"]


def test_an_unclassified_declared_source_is_still_not_evaluated(es):
    got = E.check_sentence("We hold the abstract of that trial.", SLUG, declared=["S010"])
    assert got[0]["verdict"] == "NOT EVALUATED"
    assert got[0]["why"] == "document_class not set on this source"


def test_the_field_is_read_from_bindings_when_not_passed(es, monkeypatch):
    monkeypatch.setattr(E, "store_subjects", lambda s, slug: ["S003"])
    got = E.check_sentence(T01_S17["sentence"], SLUG)
    assert got[0]["verdict"] == "PASS" and es == []


def test_a_row_without_the_field_resolves_from_the_text_as_before(es):
    got = E.check_sentence("We hold the abstract of this review.", SLUG)
    assert es == ["We hold the abstract of this review."]
    assert got[0]["verdict"] == "NOT EVALUATED" and got[0]["why"] == "no source resolved"


@pytest.mark.parametrize("sent,asserted", [
    ("We have not opened that meta-analysis.", "UNREAD"),
    ("We did not obtain the investigators' own summary paper.", "UNREAD"),
    ("Our search for a final version was limited to the Task Force's own website.",
     "HOLD"),
    ("We have opened it.", "READ"),                  # unchanged
])
def test_the_new_phrasings_are_read(sent, asserted):
    assert E._asserted(sent) == asserted


def test_store_subjects_reads_rests_on_store_from_the_case_bindings(tmp_path, monkeypatch):
    import json
    (tmp_path / "bindings.json").write_text(json.dumps({"bindings": {
        "a": {"sentence": "We hold one news report.", "rests_on_store": ["S008"]},
        "b": {"sentence": "We hold two.", "premises": [{"source_id": "S001"}]}}}))
    monkeypatch.setattr(E.store, "case_dir", lambda slug: tmp_path)
    assert E.store_subjects("We hold  one news report.", SLUG) == ["S008"]
    assert E.store_subjects("We hold two.", SLUG) == []


# --- round 3: "only" holdings ----------------------------------------------

ABSTRACT_ONLY_SENTENCES = [
    T01_S17["sentence"],                                              # T01 s17
    "We hold only the abstract of this review, from its bibliographic record.",
    "We hold the abstract of this trial, not the full paper.",        # T03 s28
    "We hold the abstract of that meta-analysis, not the full paper.",  # T04 s26
    "We hold the guideline's abstract only.",                         # T04 s47
]


def _src(sid, state, **kw):
    return dict({"id": sid, "document_class": "document", "access": {"state": state}}, **kw)


@pytest.mark.parametrize("sent", ABSTRACT_ONLY_SENTENCES)
def test_abstract_only_passes_on_abstract_held(sent, monkeypatch):
    monkeypatch.setattr(E, "_sources", lambda slug: [_src("S001", "abstract_held")])
    got = E.check_sentence(sent, SLUG, declared=["S001"])
    assert [(v["verdict"], v["asserted"]) for v in got] == [("PASS", E.ABSTRACT_ONLY)]


@pytest.mark.parametrize("state", ["full_text_held", "human_read", "blocked", "not_opened"])
@pytest.mark.parametrize("sent", ABSTRACT_ONLY_SENTENCES)
def test_abstract_only_fails_on_any_other_state(sent, state, monkeypatch):
    monkeypatch.setattr(E, "_sources", lambda slug: [_src("S001", state)])
    got = E.check_sentence(sent, SLUG, declared=["S001"])
    assert got[0]["verdict"] == "FAIL" and got[0]["recorded"] == state


def test_a_plain_hold_still_passes_on_full_text(monkeypatch):
    monkeypatch.setattr(E, "_sources", lambda slug: [_src("S008", "full_text_held")])
    got = E.check_sentence("We hold one news report.", SLUG, declared=["S008"])
    assert [(v["verdict"], v["asserted"]) for v in got] == [("PASS", "HOLD")]


# --- round 3: documents mentioned but not held -----------------------------

class _NoEntry(_Epistemic):
    def __init__(self, named=()):
        super().__init__()
        self.named = list(named)

    def _sources(self, slug):
        return [{"id": "S001"}]

    def resolve(self, sentence, slug):
        return self.named


def test_a_holdings_sentence_naming_no_source_stops_as_not_in_sources(monkeypatch):
    """T02 s46, s61, T04 s46 once their citations are removed."""
    monkeypatch.setitem(sys.modules, "epistemic", _NoEntry())
    row = {"sentence": "We have not opened that meta-analysis.", "bucket": "deterministic"}
    assert ("B21", B.NOT_IN_SOURCES) in verdicts(row)
    assert B.CALIBRATION_SEVERITY[B.NOT_IN_SOURCES] == B.BAD


def test_a_declared_id_with_no_entry_stops_as_not_in_sources(monkeypatch):
    monkeypatch.setitem(sys.modules, "epistemic", _NoEntry())
    row = {"sentence": "We have not opened that meta-analysis.",
           "bucket": "deterministic", "rests_on_store": ["S099"]}
    assert ("B21", B.NOT_IN_SOURCES) in verdicts(row)


def test_an_undeclared_sentence_naming_a_registered_source_only_warns(monkeypatch):
    """The two published sentences the first version wrongly stopped on."""
    monkeypatch.setitem(sys.modules, "epistemic", _NoEntry(named=["S010"]))
    row = {"sentence": "We have not opened Sparrow, Liu and Wegner's 2011 Science paper, "
                       "which is paywalled.", "bucket": None}
    got = verdicts(row)
    assert ("B21", "holdings sentence not declared to the store") in got
    assert ("B21", B.NOT_IN_SOURCES) not in got
    assert B.BAD not in severity(row)


@pytest.mark.parametrize("sent", ["We have not opened that meta-analysis.",
                                  "We did not obtain the investigators' summary paper."])
@pytest.mark.parametrize("state", ["not_opened", "blocked", "fragment_only",
                                   "abstract_held"])
def test_not_opened_or_not_obtained_passes_on_an_unread_or_unheld_entry(sent, state,
                                                                       monkeypatch):
    monkeypatch.setattr(E, "_sources", lambda slug: [_src("S020", state)])
    assert E.check_sentence(sent, SLUG, declared=["S020"])[0]["verdict"] == "PASS"


@pytest.mark.parametrize("sent", ["We have not opened that meta-analysis.",
                                  "We did not obtain the investigators' summary paper."])
@pytest.mark.parametrize("state", ["full_text_held", "human_read"])
def test_not_opened_or_not_obtained_fails_when_the_entry_shows_it_held(sent, state,
                                                                      monkeypatch):
    monkeypatch.setattr(E, "_sources", lambda slug: [_src("S020", state)])
    assert E.check_sentence(sent, SLUG, declared=["S020"])[0]["verdict"] == "FAIL"


# --- round 3: document_class at creation -----------------------------------

@pytest.mark.parametrize("src,klass", [
    ({"type": "primary"}, "document"),                     # TYPES: article
    ({"type": "registry"}, "document"),                    # TYPES: record -- the record IS it
    ({"type": "guideline"}, "document"),
    ({"type": "corrigendum"}, "document"),                 # notice
    ({"type": "coverage"}, "document"),                    # page
    ({"type": "critique", "form": "article"}, "document"),
    ({"type": "reference"}, "record_about"),               # RECORD_TYPES
    ({"type": "primary", "form": "record"}, "record_about"),   # S030's shape
    ({"type": "primary", "access": {"sections": ["bibliographic record"]}}, "record_about"),
    ({"type": "critique"}, "unclassified"),                # TYPES leaves the form open
    ({"type": "prior_art"}, "unclassified"),
    ({"type": "a-type-nobody-declared"}, "unclassified"),
    ({}, "unclassified"),
])
def test_document_class_of(src, klass, monkeypatch):
    monkeypatch.syspath_prepend(str(WHU))
    assert E.document_class_of(src) == klass


def test_an_unclassified_source_is_reported_by_b21_not_silently(monkeypatch):
    stub = _Epistemic()
    stub.check_sentence = lambda s, slug, declared=None: [
        {"verdict": "NOT EVALUATED", "source": "S004", "class": "unclassified",
         "why": "document_class is unclassified on this source"}]
    monkeypatch.setitem(sys.modules, "epistemic", stub)
    row = {"sentence": "We hold the abstract of this trial, not the full paper.",
           "bucket": "deterministic", "rests_on_store": ["S004"]}
    assert verdicts(row) == [("B21", "source unclassified")]
    assert B.CALIBRATION_SEVERITY["source unclassified"] == B.WARN


def test_epistemic_marks_an_explicitly_unclassified_source(monkeypatch):
    monkeypatch.setattr(E, "_sources", lambda slug: [
        {"id": "S004", "document_class": "unclassified", "access": {"state": "abstract_held"}}])
    got = E.check_sentence("We hold the abstract of this trial.", SLUG, declared=["S004"])
    assert got[0]["verdict"] == "NOT EVALUATED" and got[0]["class"] == "unclassified"


L = _load("source_ledger")


@pytest.fixture
def scratch_store(tmp_path, monkeypatch):
    """A scratch case directory; the ledger's CASES points at it, nothing else moves."""
    import json
    case = tmp_path / "WHU-999-scratch"
    case.mkdir()
    (case / "sources.json").write_text(json.dumps({"sources": [
        {"id": "S001", "type": "synthesis", "title": "Lane et al.",
         "access": {"state": "full_text_held"}}]}))
    monkeypatch.setattr(L, "CASES", tmp_path)
    monkeypatch.syspath_prepend(str(WHU))
    return case


def test_add_unread_creates_a_not_opened_entry_with_its_class(scratch_store):
    import json
    e = L.add_unread("scratch", "S002", title="The meta-analysis Lane et al. cite on "
                     "diet-quality adjustment", stype="synthesis", by="Fred Ugast",
                     mentioned="T02 s45-s46", on="2026-10-17")
    held = json.loads((scratch_store / "sources.json").read_text())["sources"]
    assert held[-1] == e
    assert e["access"] == {"state": "not_opened", "by": "Fred Ugast", "on": "2026-10-17",
                           "not_read": ["all -- not held"]}
    assert e["access"]["state"] in L.STATES            # an existing state, not a new one
    assert e["document_class"] == "document"
    assert held[0]["id"] == "S001" and "document_class" not in held[0]   # no back-fill


def test_add_unread_writes_unclassified_when_it_cannot_tell(scratch_store):
    e = L.add_unread("scratch", "S002", title="A comment", stype="critique", by="Fred Ugast")
    assert e["document_class"] == "unclassified"


def test_add_unread_refuses_an_existing_id_and_an_unnamed_recorder(scratch_store):
    with pytest.raises(ValueError):
        L.add_unread("scratch", "S001", title="x", stype="primary", by="Fred Ugast")
    with pytest.raises(ValueError):
        L.add_unread("scratch", "S003", title="x", stype="primary", by="  ")


def test_the_add_command(scratch_store, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["source_ledger.py", "add", "scratch", "S002",
                                      "--title", "Feeding study in US adolescents",
                                      "--type", "primary", "--by", "Fred Ugast"])
    assert L.main() == 0
    assert "not_opened, document_class document" in capsys.readouterr().out
