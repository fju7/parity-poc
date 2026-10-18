"""The free checks that let the paid gate narrow to figures and quotations.

Adopted 2026-10-17, after a survey of the paid gate's Phase B run on T01
(issues/WHU-T01-ctp-exercise-depression/gate/PHASE_B.md) found that its one
real error -- S5, T01 s80, "the paper's own wording is that ..." -- was a
claim no free check could see, and that six figures in the four test issues
were reported as resting on nothing while each sat in its own span printed
with a space for a thousands separator.

  A1  separators   rule 1, B12 and B13 read "14,170", "14 170", "14\\u00a0170"
                   and "14\\u2009170" as one figure, on both sides.
  A2  judgements   rule 1 holds a judgement's figures to its PREMISE spans; a
                   figure found only elsewhere in the held text does not count;
                   an undetermined premise is covered and reported apart.
  A3  rounding     a span figure correctly rounded one place shorter passes,
                   with an INFO note naming both; -0.946 shown as -0.9 or -0.94
                   does not.
  A4  B22          a claim to a source's own words: STOP when the words are in
                   no bound span and no held text; undetermined when unheld;
                   reported speech is not a wording claim.
  A5  B23          a point estimate shown without the interval its span gives:
                   INFO, never a block.

Fixtures only. Nothing here reads an issue directory or loads publish.py.
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


FT = _load("figure_text")
SC = _load("spancheck")
B = _load("bindings")
SLUG = "testissue"

# T01 s80 and its binding, copied verbatim from
# issues/WHU-T01-ctp-exercise-depression/bindings.json (row 92c82beb480ad705).
T01_S80 = ("The paper's own wording is that exercise appeared equally effective "
           "across comorbidities and baseline severity, which is an average across "
           "studies rather than a promise for each scenario.")
T01_S80_SPAN = ("Exercise appeared equally effective for people with and without "
                "comorbidities and with different baseline levels of depression.")
# What the held paper says around it (abstract, Conclusions).
S001_TEXT = ("Conclusions Walking or jogging, yoga, and strength training were more "
             "effective than other exercises, particularly when intense. Yoga and "
             "strength training were well tolerated compared with other treatments. "
             + T01_S80_SPAN + " To mitigate expectancy effects, future trials could "
             "blind participants and personnel. The pooled effect was -0.43 (95% CI "
             "-0.62 to -0.24), and 14 170 participants took part.")

HELD = {}
DEFECTIVE = set()


class _Stub:
    """spancheck over a fixture library: HELD maps a source id to its text."""
    UNDETERMINED = "undetermined"
    DROPPED_HYPHEN_NOTE = SC.DROPPED_HYPHEN_NOTE
    _norm = staticmethod(SC._norm)

    @staticmethod
    def _text(slug, sid):
        return HELD.get(sid)

    @staticmethod
    def _texts(slug, sid):
        return [("f", HELD[sid])] if sid in HELD else []

    @staticmethod
    def defective_renditions(slug, sid):
        return (sid in DEFECTIVE), "declared defective"

    @staticmethod
    def b2_present(span, slug, sid, **kw):
        doc = HELD.get(sid)
        if doc is None:
            return _Stub.UNDETERMINED, "%s is not held" % sid
        return (SC._norm(span).lower() in SC._norm(doc).lower()), "searched"


@pytest.fixture(autouse=True)
def library(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "spancheck", _Stub())
    monkeypatch.setattr(B, "path", lambda slug: tmp_path / "bindings.json")
    monkeypatch.setattr(B.store, "sources", lambda slug: [])

    def _no_page(slug):
        raise RuntimeError("no page in a fixture")
    monkeypatch.setattr(B, "_page_html", _no_page)
    HELD.clear()
    DEFECTIVE.clear()
    HELD["S001"] = S001_TEXT
    yield
    HELD.clear()
    DEFECTIVE.clear()


def put(*rows):
    doc = {"bindings": {}}
    for i, row in enumerate(rows):
        base = {"sentence": "", "sentence_sha": "R%02d" % i, "on_page": True,
                "bucket": "context", "source_id": None, "span": None,
                "premises": [], "step": ""}
        base.update(row)
        doc["bindings"]["R%02d" % i] = base
    B.save(SLUG, doc)


def rule1():
    return {name: (state, detail) for name, state, detail in B.rule_rows(SLUG)}


R1 = "rule 1 — written from a document we hold"
ROUNDED = "rule 1 — figures shown rounded from their span"
UNEVALUABLE = "spans this check cannot evaluate"


# --- A1: thousands separators ------------------------------------------------

@pytest.mark.parametrize("text", ["14,170", "14 170", "14 170", "14 170",
                                  "14 170"])
def test_every_separator_reads_as_one_figure(text):
    assert FT.comma_grouped(SC._norm("in %s adults" % text)) == "in 14,170 adults"
    assert __import__("re").search(FT.figure_pattern("14170"), SC._norm(text))


@pytest.mark.parametrize("text", ["114 170", "3 14 170", "14 170 000", "141700"])
def test_a_separator_never_joins_or_splits_a_different_number(text):
    import re
    assert not re.search(FT.figure_pattern("14170"), text)


def test_a_year_followed_by_a_count_is_not_joined():
    assert FT.comma_grouped("in 2019 100 patients") == "in 2019 100 patients"


@pytest.mark.parametrize("sentence, span", [
    ("The review pooled 14,170 adults.", "a total of 14 170 participants"),
    ("The review pooled 14 170 adults.", "a total of 14,170 participants"),
    ("The review pooled 14 170 adults.", "a total of 14 170 participants"),
])
def test_rule_1_reads_separators_on_both_sides(sentence, span):
    HELD["S009"] = span
    put({"sentence": sentence, "source_id": "S009", "span": span})
    assert rule1()[R1][0] == B.OK


def test_rule_1_still_fails_a_different_number_whatever_its_separator():
    HELD["S009"] = "a total of 14 107 participants"
    put({"sentence": "The review pooled 14,170 adults.", "source_id": "S009",
         "span": "a total of 14 107 participants"})
    state, detail = rule1()[R1]
    assert state == B.BAD and "14170" in detail


def test_b12_reads_a_space_grouped_figure_as_printed(monkeypatch):
    monkeypatch.setattr(SC, "_text", lambda slug, sid: "spending was 1 234.56 dollars")
    ok, why = SC.b12_precision("1,234.56", SLUG, "S009")
    assert ok and "as printed" in why


def test_b12_still_reports_added_precision(monkeypatch):
    monkeypatch.setattr(SC, "_text", lambda slug, sid: "HR=0.51 in the release")
    ok, why = SC.b12_precision("0.510", SLUG, "S009")
    assert not ok and "0.51" in why


def test_b13_finds_a_space_grouped_figure_in_held_text(monkeypatch):
    b13 = _load("b13")
    monkeypatch.setattr(b13.store, "held", lambda slug: {"S001": {}})
    monkeypatch.setattr(b13.SC, "_text", lambda slug, sid: S001_TEXT)
    assert b13.where("14170", SLUG) == ["S001"]
    monkeypatch.setattr(b13.B, "page_sentences",
                        lambda slug: ["The review pooled 14 170 adults."])
    assert [f for f, _ in b13.figures_on_page(SLUG)] == ["14170"]


# --- A2: a judgement's figures rest on its premises ---------------------------

JUDGEMENT = {"bucket": "judgement", "step": "the pooled effect is the review's"}


def test_a_judgement_figure_in_a_premise_span_passes():
    put(dict(JUDGEMENT, sentence="An effect of -0.43 is moderate.",
             premises=[{"source_id": "S001", "span": "The pooled effect was -0.43"}]))
    assert rule1()[R1][0] == B.OK


def test_a_judgement_figure_in_no_premise_span_fails():
    put(dict(JUDGEMENT, sentence="An effect of -0.62 is moderate.",
             premises=[{"source_id": "S001", "span": "The pooled effect was -0.43"}]))
    state, detail = rule1()[R1]
    assert state == B.BAD and "0.62" in detail


def test_a_judgement_figure_found_only_elsewhere_in_the_held_text_fails():
    # -0.62 IS in S001's held text (the interval), but not in the premise span.
    assert "-0.62" in S001_TEXT
    put(dict(JUDGEMENT, sentence="An effect as large as -0.62 is possible.",
             premises=[{"source_id": "S001", "span": "The pooled effect was -0.43"}]))
    assert rule1()[R1][0] == B.BAD


def test_an_undetermined_premise_covers_its_figures_and_is_reported_apart():
    put(dict(JUDGEMENT, sentence="An effect of -0.51 is moderate.",
             premises=[{"source_id": "S404", "span": "the effect was -0.51"}]))
    rows = rule1()
    assert rows[R1][0] == B.OK
    assert rows[UNEVALUABLE][0] == B.WARN


# --- A3: rounding -------------------------------------------------------------

@pytest.mark.parametrize("value, printed", [("0.946", "0.95"), ("-0.946", "-0.95"),
                                            ("0.43", "0.4"), ("0.008", "0.01")])
def test_one_place_correct_rounding(value, printed):
    assert FT.rounds_to(value, printed)


@pytest.mark.parametrize("value, printed", [
    ("0.946", "0.9"),     # two places, not one
    ("0.946", "0.94"),    # a truncation
    ("0.43", "0.5"),      # wrong
    ("14.2", "14"),       # rule 1 never reads an integer as a rounding
])
def test_not_a_one_place_correct_rounding(value, printed):
    assert not FT.rounds_to(value, printed)


SPAN_21 = "SMD -0.946 for walking and -0.43 for yoga"


def test_correct_rounding_passes_rule_1_with_a_note_naming_both_values():
    HELD["S009"] = SPAN_21
    put({"sentence": "Walking was about -0.95 and yoga roughly -0.4.",
         "source_id": "S009", "span": SPAN_21})
    rows = rule1()
    assert rows[R1][0] == B.OK
    state, note = rows[ROUNDED]
    assert state == B.OK and note.startswith("INFO")
    assert "0.95 is 0.946 rounded" in note and "0.4 is 0.43 rounded" in note


@pytest.mark.parametrize("shown", ["-0.9", "-0.94"])
def test_incorrect_rounding_fails_rule_1_as_a_mismatch(shown):
    HELD["S009"] = SPAN_21
    put({"sentence": "Walking was about %s." % shown, "source_id": "S009",
         "span": SPAN_21})
    rows = rule1()
    assert rows[R1][0] == B.BAD and shown.lstrip("-") in rows[R1][1]
    assert ROUNDED not in rows


def test_b12_uses_the_same_rounding_rule():
    src = (WHU / "spancheck.py").read_text(encoding="utf-8")
    body = src[src.index("def b12_precision"):]
    assert "rounds_to(" in body and '("%%.%df" % keep)' not in body


# --- A4: B22, wording claims --------------------------------------------------

def s80_row(**kw):
    row = {"sentence": T01_S80, "bucket": "context", "on_page": True,
           "source_id": "S001", "span": T01_S80_SPAN}
    row.update(kw)
    return row


def test_the_t01_s80_wording_claim_is_a_stop():
    found = B.b22_wording_claim(s80_row(), SLUG)
    assert [f["check"] for f in found] == ["B22"]
    f = found[0]
    assert f["verdict"] == "wording claim not in its source"
    assert B.CALIBRATION_SEVERITY[f["verdict"]] == B.BAD
    assert "exercise appeared equally effective across comorbidities" in f["why"]
    assert T01_S80_SPAN in f["why"]          # the nearest held sentence


def test_a_wording_claim_that_matches_the_source_passes():
    row = s80_row(sentence="The paper's own wording is that exercise appeared "
                           "equally effective for people with and without "
                           "comorbidities, which is an average.")
    assert B.b22_wording_claim(row, SLUG) == []


@pytest.mark.parametrize("phrase", ["in its words,", "in their words:", "verbatim:",
                                    "word for word:", "in its own words,",
                                    "verbatim \u201c", "word for word \""])
def test_every_wording_phrase_is_checked(phrase):
    row = s80_row(sentence="The review says, %s exercise worked across every "
                           "subgroup we could name." % phrase)
    assert [f["verdict"] for f in B.b22_wording_claim(row, SLUG)] == \
        ["wording claim not in its source"]


def test_verbatim_with_a_colon_and_words_not_in_the_source_stops():
    row = s80_row(sentence="The abstract puts it verbatim: exercise cures depression "
                           "in every adult.")
    found = B.b22_wording_claim(row, SLUG)
    assert [f["verdict"] for f in found] == ["wording claim not in its source"]
    assert "exercise cures depression in every adult" in found[0]["why"]


@pytest.mark.parametrize("sentence", [
    # T04 98799f6c, verbatim from issues/WHU-T04-ctp-vitamin-d-over-60/bindings.json
    "In December 2024 the US Preventive Services Task Force posted a draft "
    "recommendation for postmenopausal women and men age 60 years or older that "
    "addresses this question almost word for word.",
    "We did not copy the abstract verbatim, and the summary is ours.",
])
def test_verbatim_or_word_for_word_without_colon_or_quote_does_not_flag(sentence):
    assert B.b22_wording_claim(s80_row(sentence=sentence), SLUG) == []


# melanoma 075bae72, sentence and span verbatim from
# issues/WHU-001-melanoma/bindings.json. A correct published sentence that the
# first version of B22 stopped: it claims two words, and they are in S007.
MEL_075 = ("They do not share a statistical standing: the Phase 2b\u2019s later "
           "analyses are, in its own words, descriptive only , against a one-sided "
           "alpha of 0.10, while the Phase 3 crossed a prespecified interim threshold.")
MEL_075_SPAN = ("These subsequent analyses are not intended for formal hypothesis "
                "testing (ie, are descriptive only).")


def test_a_two_word_wording_claim_that_is_in_the_source_passes():
    HELD["S007"] = ("was conducted when the last enrolled patient had been followed "
                    "for \u22652 years. " + MEL_075_SPAN + " The statistical analysis "
                    "plan prespecified ...")
    row = {"sentence": MEL_075, "bucket": "context", "on_page": True,
           "source_id": "S007", "span": MEL_075_SPAN}
    assert B.b22_wording_claim(row, SLUG) == []


def test_prefixes_go_down_to_two_words_and_never_one():
    assert B._clause_prefixes("descriptive only , against a one-sided alpha") == \
        ["descriptive only", "descriptive only , against a one-sided alpha"]
    assert B._clause_prefixes("only, against all") == ["only, against all"]


@pytest.mark.parametrize("sentence", [
    "The paper states that exercise appeared equally effective across comorbidities.",
    "The authors write that exercise appeared equally effective across severity.",
    "The review describes this as an effect equal across comorbidities.",
])
def test_reported_speech_is_not_a_wording_claim(sentence):
    assert B.b22_wording_claim(s80_row(sentence=sentence), SLUG) == []


def test_a_wording_claim_on_an_unheld_source_is_undetermined_not_stop():
    HELD.clear()
    found = B.b22_wording_claim(s80_row(), SLUG)
    assert [f["verdict"] for f in found] == ["wording claim undetermined"]
    assert B.CALIBRATION_SEVERITY[found[0]["verdict"]] == B.WARN


def test_a_wording_claim_on_a_defective_text_layer_is_undetermined():
    DEFECTIVE.add("S001")
    found = B.b22_wording_claim(s80_row(), SLUG)
    assert [f["verdict"] for f in found] == ["wording claim undetermined"]


def test_b22_and_b23_are_calibration_checks_and_run_on_every_row(monkeypatch):
    assert {"B22", "B23"} <= B.CALIBRATION_CHECKS
    monkeypatch.setattr(B, "b21_holdings", lambda row, slug: [])
    put(s80_row(span=None, source_id=None, bucket="judgement",
                premises=[{"source_id": "S001", "span": T01_S80_SPAN}],
                step="x"))
    tally = B.run_checks(SLUG)
    row = B.load(SLUG)["bindings"]["R00"]
    assert "B22" in {f["check"] for f in row["check_flags"]}
    assert tally["calibration_stop"] == 1


# --- A5: B23, omitted interval -------------------------------------------------

CI_SPAN = "The pooled effect was -0.43 (95% CI -0.62 to -0.24)"


def test_a_point_estimate_without_its_interval_is_an_info_note():
    found = B.b23_interval_omitted({"sentence": "The pooled effect was -0.43.",
                                    "source_id": "S001", "span": CI_SPAN})
    assert [f["verdict"] for f in found] == ["interval omitted"]
    assert B.CALIBRATION_SEVERITY["interval omitted"] == B.INFO
    assert "-0.62" in found[0]["why"] and "-0.24" in found[0]["why"]


@pytest.mark.parametrize("sentence", [
    "The pooled effect was -0.43 (95% CI -0.62 to -0.24).",
    "The pooled effect was -0.43, with a confidence interval from -0.62.",
    "The pooled effect was -0.43, anywhere from -0.62 to -0.24.",
])
def test_a_sentence_that_gives_the_interval_has_no_note(sentence):
    assert B.b23_interval_omitted({"sentence": sentence, "source_id": "S001",
                                   "span": CI_SPAN}) == []


def test_a_bracket_that_is_not_an_interval_is_not_read_as_one():
    assert B.span_estimates("participants aged 65 (60-70); n = 120 (45-60)") == []
    assert B.span_estimates("HR 0.510 (0.294-0.887)") == [("0.510", "0.294", "0.887")]


def test_an_info_note_alone_does_not_make_the_calibration_row_warn(monkeypatch):
    monkeypatch.setattr(B, "b21_holdings", lambda row, slug: [])
    monkeypatch.setattr(B, "rule_rows", lambda slug: [])
    HELD["S009"] = CI_SPAN
    put({"sentence": "The pooled effect was -0.43.", "source_id": "S009",
         "span": CI_SPAN, "checked_on": "x",
         "check_flags": [{"check": "B23", "verdict": "interval omitted", "why": "w"}]})
    rows = {n: (s, d) for n, s, d in B.preflight_rows(SLUG)}
    state, detail = rows["sentences surer than their sources (B19-B21)"]
    assert state == B.OK and "0 STOP, 0 warn, 1 info" in detail
    assert rows["bound sentences the span checks flagged"][0] == B.OK
