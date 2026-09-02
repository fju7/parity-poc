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
    def b2_present(span, slug, sid, **kw):
        doc = HELD.get(sid)
        if doc is None:
            return _Stub.UNDETERMINED, "%s is not held" % sid
        return (span.lower() in doc.lower()), "searched the held bytes"


@pytest.fixture(autouse=True)
def stub_store(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "spancheck", _Stub())
    monkeypatch.setattr(B, "path", lambda slug: tmp_path / "bindings.json")
    yield


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
