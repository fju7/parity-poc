"""The two writing rules must be able to fail.

Adopted 2026-09-02, after a page gate found eleven real defects and only two of
them were of the kind our string checks look for. Nine were about the page's
relation to itself: a figure with no citation, an inference presented as a
report, a subheading contradicting its own paragraph. No check that asks "is
this string in that document" can see any of those, because the sentence was
written before anyone opened a document.

  Rule 1: no factual sentence enters a draft unless it rests on a document we
          hold and have read.
  Rule 2: every inference is declared as one, and shows its premises and its
          step.

Both rules were ALREADY in the schema, unenforced -- `bucket` existed and was
null on all eighty sentences of issue one. So was the deletion rule. So was
undefined_states. Each was written down, gated nothing, and was followed by the
error it described. That is why they are here as tests and not as prose.

The grandfathering mark is the risk this file watches. It exists so adopting a
rule does not stop the issue, and it is exactly the sort of waiver that quietly
grows to cover everything. It already tried: the first version marked every
sentence on the page, which excused one written that same afternoon. The mark
is now drawn from the page as it stood in git before adoption -- evidence from
outside the file it excuses -- and the last three tests pin it shut.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"


def _load(name):
    spec = importlib.util.spec_from_file_location(
        name, WHU / ("%s.py" % name))
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


# What the page said before the rule, as the snapshot reader would report it.
BEFORE = set()


@pytest.fixture(autouse=True)
def stub_store(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "spancheck", _Stub())
    monkeypatch.setattr(B, "path", lambda slug: tmp_path / "bindings.json")
    monkeypatch.setattr(B, "_sentences_at", lambda slug, ref: set(BEFORE))
    BEFORE.clear()
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
R2 = "rule 2 — inferences flagged and shown"
BOUND = {"source_id": "S002", "span": "still alive at five years"}


def test_new_sentence_resting_on_nothing_blocks():
    put({})
    assert verdicts()[R1] == B.BAD


def test_bound_new_sentence_satisfies_rule_one():
    put(dict(BOUND, bucket="reported"))
    v = verdicts()
    assert v[R1] == B.OK and v[R2] == B.OK


def test_a_sentence_that_does_not_say_what_kind_it_is_blocks():
    put(dict(BOUND))                       # bound, but bucket is None
    assert verdicts()[R2] == B.BAD


def test_inference_without_premises_blocks():
    put(dict(BOUND, bucket="inference", step="because x, therefore y"))
    assert verdicts()[R2] == B.BAD


def test_inference_without_a_written_step_blocks():
    put(dict(BOUND, bucket="inference",
             premises=[{"source_id": "S002",
                        "span": "still alive at five years"}]))
    assert verdicts()[R2] == B.BAD


def test_inference_whose_premise_is_not_in_the_source_blocks():
    put(dict(BOUND, bucket="inference", step="because x, therefore y",
             premises=[{"source_id": "S002",
                        "span": "no such words are in that document"}]))
    assert verdicts()[R2] == B.BAD


def test_inference_whose_premise_source_is_not_held_blocks():
    """UNDETERMINED is not permission. We could not check, so it does not pass."""
    put(dict(BOUND, bucket="inference", step="because x, therefore y",
             premises=[{"source_id": "S404", "span": "anything at all"}]))
    assert verdicts()[R2] == B.BAD


def test_a_sound_inference_passes():
    put(dict(BOUND, bucket="inference",
             step="The paper reports five-year survival, so the figure the "
                  "coverage calls 'long-term' is that one.",
             premises=[{"source_id": "S002",
                        "span": "still alive at five years"}]))
    v = verdicts()
    assert v[R1] == B.OK and v[R2] == B.OK


def test_grandfathering_excuses_only_what_it_marked():
    """The waiver must not spread. One old sentence, one new one, one verdict."""
    put({"predates_the_rule": B.RULE_ADOPTED}, {})
    assert verdicts()[R1] == B.BAD, "a new unbound sentence beside an old one"


def test_the_mark_is_drawn_from_the_page_not_from_what_is_unbound():
    """The bug this caught: a sentence written the same afternoon, excused.

    Two sentences, both unbound, neither distinguishable from the other by
    anything inside bindings.json. Only one was on the page before the rule.
    """
    put({}, {})
    doc = B.load(SLUG)
    BEFORE.add(B.fingerprint(doc["bindings"]["R00"]["sentence"]))
    assert B.mark_grandfathered(SLUG, "abc123") == 1
    doc = B.load(SLUG)
    assert doc["bindings"]["R00"].get("predates_the_rule")
    assert not doc["bindings"]["R01"].get("predates_the_rule")
    assert verdicts()[R1] == B.BAD, "the sentence written today is still held"


def test_a_rewritten_sentence_is_new_writing():
    """Editing a grandfathered sentence pulls it back under the rule."""
    put({})
    doc = B.load(SLUG)
    BEFORE.add(B.fingerprint(doc["bindings"]["R00"]["sentence"]))
    assert B.mark_grandfathered(SLUG, "abc123") == 1
    assert verdicts()[R1] == B.OK
    doc = B.load(SLUG)
    doc["bindings"]["R00"]["sentence"] = "Rewritten today into something else."
    doc["bindings"]["R00"].pop("predates_the_rule")
    B.save(SLUG, doc)
    assert verdicts()[R1] == B.BAD


def test_the_debt_count_falls_when_the_debt_is_paid():
    put({"predates_the_rule": B.RULE_ADOPTED},
        {"predates_the_rule": B.RULE_ADOPTED})
    label = "sentences that predate the rule"
    before = [w for n, _, w in B.rule_rows(SLUG) if n == label][0]
    assert "2 of 2" in before
    put(dict(BOUND, bucket="reported", predates_the_rule=B.RULE_ADOPTED),
        {"predates_the_rule": B.RULE_ADOPTED})
    after = [w for n, _, w in B.rule_rows(SLUG) if n == label][0]
    assert "1 of 2" in after


def test_marking_never_excuses_a_sentence_written_after_it():
    put({}, {})
    doc = B.load(SLUG)
    for r in doc["bindings"].values():
        BEFORE.add(B.fingerprint(r["sentence"]))
    assert B.mark_grandfathered(SLUG, "abc123") == 2
    doc = B.load(SLUG)
    doc["bindings"]["NEW"] = {"sentence": "Written after the rule.",
                              "sentence_sha": "NEW", "on_page": True,
                              "bucket": None, "source_id": None, "span": None}
    B.save(SLUG, doc)
    assert verdicts()[R1] == B.BAD


def test_grandfathering_refuses_to_run_twice():
    """The waiver is carved once. A second pass would swallow the rule."""
    put({}, {})
    doc = B.load(SLUG)
    for r in doc["bindings"].values():
        BEFORE.add(B.fingerprint(r["sentence"]))
    assert B.mark_grandfathered(SLUG, "abc123") == 2
    doc = B.load(SLUG)
    doc["bindings"]["NEW"] = {"sentence": "Written after the rule.",
                              "sentence_sha": "NEW", "on_page": True,
                              "bucket": None, "source_id": None, "span": None}
    B.save(SLUG, doc)
    BEFORE.add(B.fingerprint("Written after the rule."))
    with pytest.raises(RuntimeError):
        B.mark_grandfathered(SLUG, "def456")
    assert verdicts()[R1] == B.BAD
