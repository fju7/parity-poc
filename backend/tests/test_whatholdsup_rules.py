"""The two writing rules must be able to fail, and must exempt nothing.

Adopted 2026-09-02, after two page gates on issue one produced eleven findings
that were right. Two were of the kind our string checks look for -- a span that
was not in the document it cited. Nine were not: a figure with no citation, an
inference presented as a report, a subheading contradicting its own paragraph,
a claim about what other outlets said that no held article supported. None of
those can be caught by asking "is this string in that document", because the
sentence was written before anyone opened a document. Tested against that
corpus, two rules would have prevented ten of the eleven:

  Rule 1: no factual sentence enters a draft unless it rests on a document we
          hold and have read.
  Rule 2: every inference is declared as one, and shows its premises and its
          step.

Both rules were ALREADY in the schema, unenforced -- `bucket` existed and was
null on all 365 sentences of all three issues. So was the deletion rule. So was
undefined_states. Each was written down, gated nothing, and was followed by the
error it described. That is why they are here as tests and not as prose.

NO EXEMPTION FOR WHAT WAS ALREADY WRITTEN

The first implementation grandfathered every sentence on the page, reasoning
that blocking 318 sentences would stop three issues and teach the operator to
waive the check. Drawn that way it excused a sentence written the same
afternoon. Redrawn from git it still excused sixty-four whose only claim was
that nobody had checked them yet. The editor removed it: given the state of the
drafting, every sentence in all three articles is to be revalidated or
rewritten.

The last two tests are the ones that matter most here. They fail if any
exemption -- by mark, by date, by field -- ever gets a sentence past these
rules again.
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

# A stub library: S002 is held and contains one sentence; nothing else is.
HELD = {"S002": "Sixty percent of patients were still alive at five years."}


class _Stub:
    UNDETERMINED = "undetermined"

    @staticmethod
    def _norm(text):
        return " ".join((text or "").split())

    @staticmethod
    def b2_present(span, slug, sid, **kw):
        doc = HELD.get(sid)
        if doc is None:
            return _Stub.UNDETERMINED, "%s is not held" % sid
        return (span.lower() in doc.lower()), "searched the held bytes"


@pytest.fixture(autouse=True)
def stub_store(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "spancheck", _Stub())
    monkeypatch.setattr(B, "path", lambda slug: tmp_path / "bindings.json")
    monkeypatch.setattr(B.store, "sources", lambda slug: [])
    keep = dict(HELD)
    yield
    HELD.clear()
    HELD.update(keep)


def put(*rows):
    doc = {"bindings": {}}
    for i, row in enumerate(rows):
        base = {"sentence": "Sentence number %d, about 42 patients." % i,
                "sentence_sha": "R%02d" % i, "on_page": True, "bucket": None,
                "source_id": None, "span": None, "premises": [], "step": ""}
        base.update(row)
        doc["bindings"]["R%02d" % i] = base
    B.save(SLUG, doc)


def verdicts():
    return {name: state for name, state, _ in B.rule_rows(SLUG)}


R1 = "rule 1 — written from a document we hold"
R2 = ("rule 2 — every sentence declares its kind, judgements show "
      "their work")
BOUND = {"source_id": "S002", "span": "still alive at five years"}


def test_a_sentence_resting_on_nothing_blocks():
    put({})
    assert verdicts()[R1] == B.BAD


def test_a_bound_and_declared_sentence_passes():
    put(dict(BOUND, bucket="deterministic"))
    v = verdicts()
    assert v[R1] == B.OK and v[R2] == B.OK


def test_a_sentence_that_does_not_say_what_kind_it_is_blocks():
    put(dict(BOUND))                       # bound, but bucket is None
    assert verdicts()[R2] == B.BAD


def test_judgement_without_premises_blocks():
    put(dict(BOUND, bucket="judgement", step="because x, therefore y"))
    assert verdicts()[R2] == B.BAD


def test_judgement_without_a_written_step_blocks():
    put(dict(BOUND, bucket="judgement",
             premises=[{"source_id": "S002",
                        "span": "still alive at five years"}]))
    assert verdicts()[R2] == B.BAD


def test_judgement_whose_premise_is_not_in_the_source_blocks():
    put(dict(BOUND, bucket="judgement", step="because x, therefore y",
             premises=[{"source_id": "S002",
                        "span": "no such words are in that document"}]))
    assert verdicts()[R2] == B.BAD


def test_judgement_whose_premise_source_is_not_held_blocks():
    """UNDETERMINED is not permission. We could not check, so it does not pass."""
    put(dict(BOUND, bucket="judgement", step="because x, therefore y",
             premises=[{"source_id": "S404", "span": "anything at all"}]))
    assert verdicts()[R2] == B.BAD


def test_a_sound_judgement_passes():
    put(dict(BOUND, bucket="judgement",
             step="The paper reports five-year survival, so the figure the "
                  "coverage calls 'long-term' is that one.",
             premises=[{"source_id": "S002",
                        "span": "still alive at five years"}]))
    v = verdicts()
    assert v[R1] == B.OK and v[R2] == B.OK


def test_one_bad_sentence_blocks_a_page_of_good_ones():
    """No proportion of compliance buys a pass for the rest."""
    put(*([dict(BOUND, bucket="deterministic")] * 40 + [{}]))
    assert verdicts()[R1] == B.BAD


def test_the_backlog_count_is_printed_and_falls_only_by_doing_the_work():
    label = "sentences still to revalidate"
    put({}, {})
    assert "2 of 2" in [w for n, _, w in B.rule_rows(SLUG) if n == label][0]
    put(dict(BOUND, bucket="deterministic"), {})
    assert "1 of 2" in [w for n, _, w in B.rule_rows(SLUG) if n == label][0]
    put(dict(BOUND, bucket="deterministic"), dict(BOUND, bucket="deterministic"))
    assert not [n for n, _, w in B.rule_rows(SLUG) if n == label]


def test_no_field_exempts_a_sentence_from_rule_one():
    """The exemption is gone. Nothing resembling one may bring it back.

    A row carrying every plausible waiver -- the mark the first version used, a
    date, an explicit exemption flag, a signature -- and still no span, blocks.
    """
    put({"predates_the_rule": "2026-09-02", "grandfathered": True,
         "exempt": True, "first_seen": "2020-01-01", "waived_by": "the editor",
         "reason": "written before the rule"})
    assert verdicts()[R1] == B.BAD


def test_no_field_exempts_a_sentence_from_rule_two():
    put(dict(BOUND, predates_the_rule="2026-09-02", grandfathered=True,
             exempt=True, waived_by="the editor"))
    assert verdicts()[R2] == B.BAD


def test_the_grandfathering_machinery_is_gone():
    """Not merely unused -- absent. An unused waiver is one import away."""
    assert not hasattr(B, "mark_grandfathered")
    src = (WHU / "bindings.py").read_text(encoding="utf-8")
    for token in ("predates_the_rule", "_grandfathered_from", "grandfather"):
        assert token not in src, "%s survives in bindings.py" % token


def test_a_bucket_outside_the_spec_vocabulary_blocks():
    """No new words. BUCKETS is the spec's list and the only list."""
    put(dict(BOUND, bucket="reported"))
    assert verdicts()[R2] == B.BAD
    put(dict(BOUND, bucket="inference"))
    assert verdicts()[R2] == B.BAD, "the name the first draft invented"


def test_a_figure_based_sentence_needs_a_named_human_and_a_record():
    """Spec s3: for a figure-based sentence 'locatable' is NOT POSSIBLE.

    The NCCN guideline's licence forbids putting it through any automated tool,
    so no check will ever read it. A sentence resting on it is bound by the
    operator's recorded reading, and the row must say who read it, where that
    reading is written down, and where in the document to look. A machine that
    reported such a span as verified would be claiming to have read a document
    it is forbidden to open.
    """
    put(dict(BOUND, bucket="figure"))
    assert verdicts()[R2] == B.BAD
    put(dict(BOUND, bucket="figure", attested_by="fred"))
    assert verdicts()[R2] == B.BAD, "a name with no record behind it"
    put(dict(BOUND, bucket="figure", attested_by="fred",
             attested_in="advocate/2026-08-29-adjudication.md",
             locator="Categories of Preference table, BINV-Q 3 of 5"))
    assert verdicts()[R2] == B.OK


# ---------------------------------------------------------------------------
# A sentence is not bound because ONE of its figures is
# ---------------------------------------------------------------------------
#
# Found in the live corpus the hour this check was written: four sentences that
# rule 1 called bound, each carrying a figure that appeared in no span it was
# bound to. One of them -- "an open-label study of 157 patients, not the
# blinded study of 1,137" -- was bound to a trade article that contains "157"
# only inside "mRNA-4157". The count came from a different paper entirely.

TWO_FIGURES = "The trial enrolled 1,137 patients and reported 60.3 months of follow-up."


def test_a_figure_in_no_bound_span_blocks():
    HELD["S100"] = "The trial enrolled 1,137 patients in total."
    put({"sentence": TWO_FIGURES, "on_page": True, "bucket": "deterministic",
         "source_id": "S100", "span": "enrolled 1,137 patients"})
    assert verdicts()[R1] == B.BAD, "60.3 is in no span this sentence is bound to"


def test_a_second_span_covers_the_second_figure():
    HELD["S100"] = "The trial enrolled 1,137 patients in total."
    HELD["S101"] = "Median follow-up was 60.3 months at data cutoff."
    put({"sentence": TWO_FIGURES, "on_page": True, "bucket": "deterministic",
         "source_id": "S100", "span": "enrolled 1,137 patients",
         "also_rests_on": [{"source_id": "S101",
                            "span": "follow-up was 60.3 months"}]})
    assert verdicts()[R1] == B.OK


def test_a_second_span_that_is_not_in_its_document_blocks():
    """An extra span is evidence only if it is really there."""
    HELD["S100"] = "The trial enrolled 1,137 patients in total."
    HELD["S101"] = "Median follow-up was 60.3 months at data cutoff."
    put({"sentence": TWO_FIGURES, "on_page": True, "bucket": "deterministic",
         "source_id": "S100", "span": "enrolled 1,137 patients",
         "also_rests_on": [{"source_id": "S101",
                            "span": "follow-up was 71.2 months"}]})
    assert verdicts()[R1] == B.BAD


def test_a_number_inside_an_identifier_is_not_a_figure():
    """KEYNOTE-942 is a name. mRNA-4157 is a name. Neither is a measurement.

    Stated as a rule about token shape, not as a list of the identifiers we
    have happened to meet -- every allowlist built from met vocabulary in this
    repository has turned out wrong.
    """
    assert "942" not in B._claim_figures("KEYNOTE-942 reported its result.")
    assert "4157" not in B._claim_figures("intismeran (V940 or mRNA-4157)")
    assert "1137" in B._claim_figures("The trial enrolled 1,137 patients.")
    assert "05933577" not in B._claim_figures("the registry record NCT05933577")


def test_the_identifier_rule_does_not_hide_a_real_figure_beside_a_name():
    got = B._claim_figures("KEYNOTE-942 enrolled 157 patients.")
    assert "157" in got and "942" not in got


# ---------------------------------------------------------------------------
# Field bindings: relevance by named path, never by loosening the prose guard
# ---------------------------------------------------------------------------

def test_bind_field_resolves_and_records_the_path(tmp_path, monkeypatch):
    import json as _json
    record = {"hasResults": False,
              "protocolSection": {"statusModule": {"overallStatus": "ACTIVE"}}}
    monkeypatch.setattr(B, "_held_text",
                        lambda slug, sid: _json.dumps(record))
    monkeypatch.setattr(B.store, "held", lambda slug: {"S013": {"sha256": "x"}})
    put({})
    sha = list(B.load(SLUG)["bindings"])[0]
    ok, why = B.bind_field(SLUG, sha, "S013", "hasResults")
    assert ok, why
    row = B.load(SLUG)["bindings"][sha]
    assert row["locator"] == "$.hasResults"
    assert row["locator_type"] == "field"
    assert row["span"] == '"hasResults":false'


def test_bind_field_refuses_a_path_that_does_not_resolve(tmp_path, monkeypatch):
    import json as _json
    monkeypatch.setattr(B, "_held_text", lambda slug, sid: _json.dumps({"a": 1}))
    monkeypatch.setattr(B.store, "held", lambda slug: {"S013": {"sha256": "x"}})
    put({})
    sha = list(B.load(SLUG)["bindings"])[0]
    ok, why = B.bind_field(SLUG, sha, "S013", "a.b.c")
    assert not ok and "does not resolve" in why
    assert not B.load(SLUG)["bindings"][sha].get("span"), "nothing written on failure"


def test_bind_field_refuses_a_document_that_is_not_json(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "_held_text", lambda slug, sid: "a press release")
    monkeypatch.setattr(B.store, "held", lambda slug: {"S013": {"sha256": "x"}})
    put({})
    sha = list(B.load(SLUG)["bindings"])[0]
    ok, why = B.bind_field(SLUG, sha, "S013", "hasResults")
    assert not ok and "not JSON" in why


# ---------------------------------------------------------------------------
# A judgement satisfies rule 1 through its premises, and pays more for it
# ---------------------------------------------------------------------------

def test_a_judgement_with_premises_satisfies_rule_one_without_its_own_span():
    put({"sentence": "So the two figures are the same result.", "on_page": True,
         "bucket": "judgement", "step": "One is the one-sided p and the other "
         "the two-sided p for the same comparison.",
         "premises": [{"source_id": "S002",
                       "span": "still alive at five years"}]})
    v = verdicts()
    assert v[R1] == B.OK and v[R2] == B.OK


def test_declaring_a_judgement_is_not_a_way_out_of_rule_one():
    """It buys strictly more work, which is what keeps the bucket honest."""
    put({"sentence": "So the two figures are the same result.", "on_page": True,
         "bucket": "judgement"})
    v = verdicts()
    assert v[R1] == B.BAD, "no premises means nothing it rests on"
    assert v[R2] == B.BAD, "and no step written out"


def test_a_judgements_figures_must_be_in_its_premises():
    HELD["S100"] = "The trial enrolled 1,137 patients in total."
    put({"sentence": "Reading 1,137 beside 60.3 months is what misleads.",
         "on_page": True, "bucket": "judgement", "step": "because x",
         "premises": [{"source_id": "S100", "span": "enrolled 1,137 patients"}]})
    assert verdicts()[R1] == B.BAD, "60.3 is in no premise"


def test_a_report_still_needs_its_own_span():
    put({"sentence": "The trial enrolled 1,137 patients.", "on_page": True,
         "bucket": "deterministic"})
    assert verdicts()[R1] == B.BAD


def test_a_figure_is_covered_by_the_same_number_spelled_differently():
    """1.0 and 1 are the same number. So are 0.51 and 0.510, and 1,137 and 1137."""
    HELD["S100"] = "If HR = 1 then the two hazard functions are equal."
    put({"sentence": "An HR of 1.0 means the groups' hazard rates are the same.",
         "on_page": True, "bucket": "context",
         "source_id": "S100", "span": "If HR = 1 then the two hazard functions"})
    assert verdicts()[R1] == B.OK


def test_numeric_comparison_does_not_cover_a_figure_that_is_absent():
    HELD["S100"] = "If HR = 1 then the two hazard functions are equal."
    put({"sentence": "An HR of 0.51 halves the hazard.", "on_page": True,
         "bucket": "context", "source_id": "S100",
         "span": "If HR = 1 then the two hazard functions"})
    assert verdicts()[R1] == B.BAD


def test_a_name_with_a_space_in_it_is_still_a_name():
    """"CheckMate 238" is two tokens, so the token-shape rule alone missed it.

    The names come from the source ledger's own `also_called` lists — what this
    issue's documents are called — not from a list of trials I happened to meet.
    """
    got = B._claim_figures("That rests on CheckMate 238 and KEYNOTE-054.",
                           {"CheckMate 238", "KEYNOTE-054"})
    assert "238" not in got and "054" not in got


def test_a_real_figure_beside_a_spaced_name_survives():
    got = B._claim_figures("CheckMate 238 enrolled 906 patients.",
                           {"CheckMate 238"})
    assert "906" in got and "238" not in got


# ---------------------------------------------------------------------------
# An attestation is not a span, satisfies rule 1, and is counted apart
# ---------------------------------------------------------------------------
#
# NCCN's licence forbids putting the guideline through any automated tool. No
# check has read it or ever may. A rule 1 that demanded a span from sentences
# resting on it would push us toward pasting licence-bound text into a file to
# satisfy a check — the worst outcome available.

ATTESTED = {"bucket": "figure", "source_id": "S001",
            "attested_by": "fred",
            "attested_in": "advocate/2026-08-29-adjudication.md",
            "locator": "Categories of Evidence and Consensus, front matter"}


def test_a_complete_attestation_satisfies_both_rules_without_a_span():
    put(dict(ATTESTED, sentence="The guideline assigns ribociclib category 1."))
    v = verdicts()
    assert v[R1] == B.OK and v[R2] == B.OK


def test_an_incomplete_attestation_satisfies_neither():
    for missing in ("attested_by", "attested_in", "locator"):
        row = dict(ATTESTED, sentence="The guideline assigns ribociclib category 1.")
        row[missing] = ""
        put(row)
        assert verdicts()[R1] == B.BAD, "missing %s" % missing
        assert verdicts()[R2] == B.BAD, "missing %s" % missing


def test_an_attestation_is_reported_apart_from_verified_spans():
    """"A human says so about a document nothing may read" and "this string is
    in these bytes" are different claims. Merging them is the oldest error here."""
    put(dict(ATTESTED, sentence="The guideline assigns ribociclib category 1."),
        dict(BOUND, bucket="deterministic",
             sentence="Sixty percent were alive at five years."))
    rows = {n: w for n, _, w in B.rule_rows(SLUG)}
    label = "sentences resting on a human attestation"
    assert label in rows
    assert "1 of 2" in rows[label]
    assert "never counted as one" in rows[label]


def test_the_figure_bucket_does_not_excuse_a_sentence_from_a_bucket_check():
    """It buys a different obligation, not a lighter one."""
    put({"sentence": "The guideline assigns ribociclib category 1.",
         "on_page": True, "bucket": "figure"})
    assert verdicts()[R2] == B.BAD, "no attestation at all"


def test_a_figure_resting_only_on_reporting_is_reported(monkeypatch):
    """"Every number traces to a primary document" must be enforced, not asserted.

    The outside review of 2026-09-03 found the page claiming no number came
    from a news report while its five-year rates were credited to a trade
    article. The abstract was obtained by hand and they moved; this check is
    why the claim can be made again.
    """
    monkeypatch.setattr(B.store, "sources", lambda slug: [
        {"id": "S100", "type": "coverage"}, {"id": "S200", "type": "primary"}])
    HELD["S100"] = "The trial enrolled 1,137 patients in total."
    put({"sentence": "The trial enrolled 1,137 patients.", "on_page": True,
         "bucket": "context", "source_id": "S100",
         "span": "enrolled 1,137 patients"})
    assert B.figures_resting_only_on_reporting(SLUG)
    rows = {n: s for n, s, _ in B.rule_rows(SLUG)}
    assert rows["figures resting only on somebody's reporting"] == B.BAD


def test_a_quotation_from_an_outlet_is_not_flagged(monkeypatch):
    """Only sentences carrying FIGURES. An outlet's words belong to the outlet."""
    monkeypatch.setattr(B.store, "sources", lambda slug: [
        {"id": "S100", "type": "coverage"}])
    HELD["S100"] = "The companies did not disclose hazard ratios."
    put({"sentence": "Practical Dermatology: the companies did not disclose hazard ratios.",
         "on_page": True, "bucket": "context", "source_id": "S100",
         "span": "did not disclose hazard ratios"})
    assert not B.figures_resting_only_on_reporting(SLUG)



# --- what the checks are allowed to see -------------------------------------

def test_covering_spans_include_also_rests_on():
    row = {"source_id": "S1", "span": "a", "bucket": "context",
           "also_rests_on": [{"source_id": "S2", "span": "b"}],
           "premises": [{"source_id": "S3", "span": "c"}]}
    assert B.covering_spans(row) == [("S1", "a"), ("S2", "b")]


def test_covering_spans_include_premises_for_a_judgement_only():
    """A judgement's whole claim to rule 2 is that its step runs over them."""
    row = {"source_id": "S1", "span": "a", "bucket": "judgement",
           "premises": [{"source_id": "S3", "span": "c"}]}
    assert ("S3", "c") in B.covering_spans(row)


def test_covering_spans_drop_a_premise_nobody_attributed():
    """Not attributed to the primary source as a kindness.

    A premise with a span and no source is the writer failing to say where it
    came from. Defaulting it to whatever the row's main source happens to be
    would have the check attribute a claim on their behalf, which is the one
    thing this layer exists not to do.
    """
    row = {"source_id": "S1", "span": "a", "bucket": "judgement",
           "premises": [{"span": "c"}, {"source_id": "S4"}]}
    assert B.covering_spans(row) == [("S1", "a")]


def test_a_scope_word_carried_by_a_secondary_span_is_mapped():
    """B6 was handed row["span"] alone on a row that named three documents.

    It then said "descriptive only" had no span carrying "only", on a row whose
    also_rests_on is the sentence 'These subsequent analyses are not intended
    for formal hypothesis testing (ie, are descriptive only).' The check was
    right about the span it was given, and the span it was given was one of
    three. Same shape as b12_precision's founding bug, one layer up.
    """
    SC = _load("spancheck")
    sent = ("the paper states plainly that its analyses were descriptive only "
            "and not intended for formal hypothesis testing")
    primary = "HR 0.510 95% CI 0.288 to 0.906"
    secondary = ("These subsequent analyses are not intended for formal "
                 "hypothesis testing (ie, are descriptive only).")
    assert any(w == "only" for w, _ in SC.b6_scope(sent, primary))
    joined = "   ".join([primary, secondary])
    assert not any(w == "only" for w, _ in SC.b6_scope(sent, joined))


def test_the_page_title_is_not_a_sentence_on_the_page():
    """<title> is a text node with no full stop, so it glued itself to the
    first thing after it and arrived as

        "The Melanoma Result - What Holds Up 1,137 patients in the Phase 3 trial"

    which B5 then checked against a press release as though someone wrote it.
    """
    html = ('<html><head><title>The Melanoma Result</title>'
            '<meta name="description" content="released no Phase 3 numbers">'
            '</head><body><div><b>1,137</b><span>patients</span></div>'
            '</body></html>')
    assert "The Melanoma Result" not in B.HEAD.sub(" ", html)
    assert "1,137" in B.HEAD.sub(" ", html)


# --- a negation can be a value rather than a word ----------------------------

FIELD = [("S013", '"hasResults":false')]


def test_a_boolean_false_carries_the_negation():
    """The registry record contains no "no results", no "not posted", no
    "none" anywhere in it. The negation is a JSON boolean, and B6 was looking
    for a word."""
    row = {"locator": "$.hasResults", "span": '"hasResults":false',
           "source_id": "S013"}
    assert B.field_negation(row, FIELD)


def test_a_true_value_carries_nothing():
    """The control has to be able to fail, or it is an exemption."""
    row = {"locator": "$.hasResults", "span": '"hasResults":true',
           "source_id": "S013"}
    assert B.field_negation(row, [("S013", '"hasResults":true')]) == ""


def test_a_field_with_no_locator_carries_nothing():
    """Relevance is the named field path. A structured-looking span nobody
    bound by path is prose that happens to contain a colon."""
    row = {"span": '"hasResults":false', "source_id": "S013"}
    assert B.field_negation(row, FIELD) == ""


def test_one_field_cannot_carry_a_claim_wider_than_itself():
    """The case that shaped the rule.

    "no hazard ratio ... appears in either company release, in any of the
    specialist or general coverage we hold, or in the trial's own registry
    record" ALSO rests on $.hasResults. That field settles the registry clause
    and says nothing whatever about the coverage. Clearing its negation on the
    strength of one boolean would be the check reporting an absence over
    documents it never looked at — this repository's oldest error, committed by
    the fix for it.
    """
    row = {"locator": "$.protocolSection...date", "source_id": "S013",
           "span": '"date":"2029-10-26"'}
    cover = [("S013", '"date":"2029-10-26"'), ("S013", '"hasResults":false')]
    assert B.field_negation(row, cover) == ""


def test_the_field_reading_clears_negations_and_not_quantifiers():
    """A boolean says "not so". It does not say "every", "any" or "only"."""
    assert "no" in B.NEGATION_WORDS and "none" in B.NEGATION_WORDS
    for w in ("any", "all", "every", "each", "only"):
        assert w not in B.NEGATION_WORDS


# --- a quantifier over named things is a count -------------------------------

TWO_TRIALS = [{"id": "S020", "also_called": ["KEYNOTE-054"]},
              {"id": "S026", "also_called": ["KEYNOTE-716"]},
              {"id": "S021", "also_called": ["CheckMate 238"]}]
SENT = ("KEYNOTE-054 and KEYNOTE-716 are both pembrolizumab against placebo; "
        "each registry record marks that result NOT_POSTED.")


def test_each_is_mapped_when_the_row_rests_on_every_trial_named(monkeypatch):
    """No span will ever contain the force of "each". It is not a word to be
    matched; it is a claim that the row rests on every thing the sentence
    names, and that is a count."""
    monkeypatch.setattr(B.store, "sources", lambda slug: TWO_TRIALS)
    cover = [("S020", '"reportingStatus":"NOT_POSTED"'),
             ("S026", '"reportingStatus":"NOT_POSTED"')]
    assert B.enumeration_covered(SENT, cover, SLUG)


def test_each_is_not_mapped_when_a_named_trial_is_missing(monkeypatch):
    """The whole point. Cite one record, leave "each" in the sentence, and the
    count comes up short."""
    monkeypatch.setattr(B.store, "sources", lambda slug: TWO_TRIALS)
    cover = [("S020", '"reportingStatus":"NOT_POSTED"')]
    assert B.enumeration_covered(SENT, cover, SLUG) == ""


def test_one_named_thing_is_not_an_enumeration(monkeypatch):
    """A quantifier over one thing is not a quantifier."""
    monkeypatch.setattr(B.store, "sources", lambda slug: TWO_TRIALS)
    sent = "KEYNOTE-054's registry record marks every result NOT_POSTED."
    assert B.enumeration_covered(sent, [("S020", "x")], SLUG) == ""


def test_a_sentence_naming_nothing_is_not_an_enumeration(monkeypatch):
    monkeypatch.setattr(B.store, "sources", lambda slug: TWO_TRIALS)
    sent = "Each of the trials we hold lists overall survival as secondary."
    assert B.enumeration_covered(sent, [("S020", "x"), ("S026", "y")], SLUG) == ""


def test_only_the_distributive_quantifiers_are_counted():
    """"all" and "any" usually range over a corpus nobody enumerated — "any of
    the specialist coverage we hold", "no posted results at all" — and a count
    of named trials says nothing about those."""
    assert B.ENUMERATING == {"each", "every", "both"}
    for w in ("all", "any", "no", "none", "only"):
        assert w not in B.ENUMERATING

