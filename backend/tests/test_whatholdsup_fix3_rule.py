"""Fix 3, step 3: every relevant held assessment judgement is stated with its
certainty, or declared (post-study, 2026-10-27). Always on.

Relevance comes from the real ruling path (ruling.rule_judgements) with the
lexical fake of the step-2 tests; the rule is judgements.preflight_rows.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import coverage_check as C                   # noqa: E402
import judgements as J                       # noqa: E402
import ruling as R                           # noqa: E402
import test_whatholdsup_fix2_coverage as CV  # noqa: E402
import test_whatholdsup_fix3_judgements as T  # noqa: E402

HELD = {"S003": CV.CHAPTER}
PARA2 = "Many more cities have developed adaptation plans, but only a limited number have been implemented"


def _rule(tmp_path, rows, held=HELD, scope=T.SCOPE):
    return dict((r[0], r) for r in J.preflight_rows("x", [], held=held, rows=rows, case=tmp_path))[J.ROW]


def _row(sentence, span=PARA2):
    return {"r1": {"on_page": True, "source_id": "S003", "span": span, "sentence": sentence}}


@pytest.fixture
def ruled(tmp_path):
    R.rule_judgements("x", T.Lexical(), P=T.P, held=HELD, scope=T.SCOPE, case=tmp_path)
    return tmp_path


def test_unruled_judgements_block(tmp_path):
    r = _rule(tmp_path, {})
    assert r[1] == J.BAD and "not yet ruled for relevance" in r[2]


def test_a_relevant_judgement_not_stated_blocks(ruled):
    r = _rule(ruled, {})
    assert r[1] == J.BAD and "neither stated with their certainty nor declared" in r[2] and "¶2" in r[2]


def test_bound_without_its_certainty_blocks_and_with_it_passes(ruled):
    r = _rule(ruled, _row("Many cities have plans, but few have been implemented."))
    assert r[1] == J.BAD and "bound without its certainty" in r[2] and "medium confidence" in r[2]
    r = _rule(ruled, _row("Many cities have plans, but few have been implemented (medium confidence)."))
    assert r[1] == J.OK and "1 stated" in r[2]


def test_a_declared_judgement_passes(ruled, monkeypatch):
    import premise as PM
    import source_store as store
    monkeypatch.setattr(store, "case_dir", lambda slug: ruled)
    para = [c for c in J.candidates(HELD) if c["section"] == "Executive Summary ¶2"][0]
    C.declare("x", para["key"], "out_of_scope", "about plans, not outcomes", "Claude Code",
              element="climate change", case=ruled)
    r = _rule(ruled, {})
    assert r[1] == J.OK and "1 declared" in r[2]


def test_a_judgement_with_a_person_blocks(tmp_path):
    bad = json.dumps({"relevant": True, "question_words": "urban heat islands", "reason": "r"})
    R.rule_judgements("x", T.Lexical(override=bad), P=T.P, held=HELD, scope=T.SCOPE, case=tmp_path)
    assert "with a person" in _rule(tmp_path, {})[2]


def test_published_before_adoption_is_skipped():
    [row] = J.preflight_rows("x", [{"issue": "x", "action": "publish", "at": "2026-09-01T00:00:00+00:00"}])
    assert row[1] == J.OK and row[2].startswith("SKIPPED")


def test_publish_carries_the_row_and_fails_closed():
    src = (WHU / "publish.py").read_text(encoding="utf-8")
    assert 'judgements = _sibling("judgements")' in src
    assert "judgements.preflight_rows(slug, load_record())" in src and "(judgements.ROW, BAD," in src


# ----------------------------------------------------------------- replays on the study pages

def _real(slug):
    import bindings as B
    if not list((ROOT / "issues").glob("WHU-S0*-%s/bindings.json" % slug)):
        pytest.skip("the study's records are private and not here")
    held = R.held_texts(slug)
    if not held:
        pytest.skip("the held texts are not here")
    return held, B.load(slug)["bindings"]


def _replay(tmp_path, slug):
    import premise as PM
    held, rows = _real(slug)
    R.rule_judgements(slug, T.Lexical(), P=T.P, held=held, scope=PM.scope_of(slug), case=tmp_path)
    flagged = []
    doc = J.load(tmp_path)
    bound = J.bound_sentences(rows, held)
    for c in J.candidates(held):
        if (doc["candidates"].get(c["key"]) or {}).get("relevant") is True:
            st, _ = J.state_of(c, held[c["source"]], rows, held, {}, {"omissions": []}, bound)
            if st in ("not stated", "bound without its certainty"):
                flagged.append(c)
    row = dict((r[0], r) for r in J.preflight_rows(slug, [], held=held, rows=rows, case=tmp_path))[J.ROW]
    return held, flagged, row


def test_replay_s08_page_is_flagged(tmp_path):
    held, flagged, row = _replay(tmp_path, "settlement-planning-climate-resilience")
    assert row[1] == J.BAD and flagged
    assert {c["source"] for c in flagged} == {"S003"}                     # the held Chapter 6
    assert all(c["section"].startswith("Executive Summary") for c in flagged)


def test_replay_s03_c1_is_flagged_through_chapter_13_paragraph_7(tmp_path):
    held, flagged, row = _replay(tmp_path, "public-involvement-climate-policy")
    t = held["S006"]
    i = t.find("a broad group of actors")
    assert row[1] == J.BAD
    assert [c["section"] for c in flagged if c["at"][0] <= i < c["at"][1]] == ["Executive Summary ¶7"]
