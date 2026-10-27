"""Fix 3, step 2: held assessment judgements and the relevance ruling (post-study, 2026-10-27).

docs/whu-fix3-evidence-standard.md s3.2, ruled R1. No model is called. The fake
relevance model is lexical and answers only from its prompt; whether its
answer is recorded is decided by code (judgements.verify_words).
"""
import json
import re
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import consistency as CS                     # noqa: E402
import judgements as J                       # noqa: E402
import ruling as R                           # noqa: E402
import stage_cap as SC                       # noqa: E402
import test_whatholdsup_fix2_coverage as CV  # noqa: E402

P = types.SimpleNamespace(is_study=lambda slug: True)
QUESTION = ("Does taking climate change into account when planning towns and infrastructure, through plans "
            "that are implemented, make them better able to cope?")
SCOPE = {"question": QUESTION, "covers": "", "out": []}
STOP = {"does", "taking", "into", "account", "when", "make", "them", "better", "able", "the", "and"}


class Lexical:
    """Relevant when at least two of the question's content words are in the
    judgement; quotes them in question order. Records every prompt."""

    def __init__(self, override=None):
        self.prompts, self.override = [], override

    def __call__(self, prompt, max_tokens, role):
        self.prompts.append(prompt)
        if self.override is not None:
            return self.override, {"usd": 0.0}
        q = re.search(r"<<<QUESTION\n(.*?)\nQUESTION>>>", prompt, re.S).group(1)
        j = re.search(r"<<<JUDGEMENT\n(.*?)\nJUDGEMENT>>>", prompt, re.S).group(1).lower()
        words = [w for w in re.findall(r"[A-Za-z]{5,}", q) if w.lower() not in STOP and w.lower() in j]
        rel = len(words) >= 2
        return json.dumps({"relevant": rel, "question_words": " … ".join(words) if rel else "",
                           "reason": "lexical"}), {"input": 10, "output": 5, "usd": 0.0}


def _run(tmp_path, held, fake, scope=SCOPE):
    return R.rule_judgements("x", fake, P=P, held=held, scope=scope, case=tmp_path)


# ----------------------------------------------------------------- candidates

def test_candidates_are_whole_assessment_paragraphs_and_review_conclusions():
    c = J.candidates({"S003": CV.CHAPTER, "S001": CV.REVIEW, "S002": CV.PRIMARY})
    secs = [(x["source"], x["section"]) for x in c]
    assert [s for s in secs if s[0] == "S003"] == [("S003", "Executive Summary ¶%d" % n) for n in (1, 2, 3)]
    assert ("S001", "abstract conclusions") in secs
    assert not [s for s in secs if s[0] == "S002"]           # a primary study's abstract is not an assessment
    para = [x for x in c if x["section"] == "Executive Summary ¶2"][0]
    assert CV.CHAPTER[para["at"][0]:para["at"][1]].count(".") >= 3   # the paragraph whole


def test_an_spm_gives_every_calibrated_statement():
    c = J.candidates({"S009": CV.SPM})
    assert len(c) == 8 and {x["kind"] for x in c} == {"assessment"}


# ----------------------------------------------------------------- relevance

def test_relevant_judgements_are_recorded_only_with_verified_question_words(tmp_path):
    held = {"S003": CV.CHAPTER}
    fake = Lexical()
    done = _run(tmp_path, held, fake)
    assert len(fake.prompts) == 3 and all(QUESTION in p for p in fake.prompts)
    doc = J.load(tmp_path)["candidates"]
    rel = {v["section"]: v["relevant"] for v in doc.values()}
    assert rel["Executive Summary ¶2"] is True        # plans ... implemented ... infrastructure? (lexical)
    assert all(v["text_sha256"] and "text" not in v for v in doc.values())
    # nothing is asked twice
    again = Lexical()
    assert _run(tmp_path, held, again) == [] and again.prompts == []


def test_words_not_in_the_question_go_to_a_person_and_are_not_re_ruled(tmp_path):
    held = {"S003": CV.CHAPTER}
    bad = json.dumps({"relevant": True, "question_words": "urban heat islands", "reason": "r"})
    done = _run(tmp_path, held, Lexical(override=bad))
    assert all(d["to_person"] for d in done)
    assert all(v["relevant"] is None and v["to_person"] for v in J.load(tmp_path)["candidates"].values())
    assert (tmp_path / "rulings" / R.FOR_PERSON).exists()
    again = Lexical()
    assert _run(tmp_path, held, again) == [] and again.prompts == []
    rule, person = J.undecided(J.candidates(held), J.load(tmp_path), held)
    assert rule == [] and len(person) == 3


def test_an_unusable_reply_goes_to_a_person(tmp_path):
    done = _run(tmp_path, {"S003": CV.CHAPTER}, Lexical(override="no json here"))
    assert all(d["to_person"] for d in done)


def test_words_from_the_scope_covers_are_accepted():
    sc = dict(SCOPE, covers="flood damage and heat stress")
    assert J.verify_words("flood damage", sc)[0] and not J.verify_words("flood damage", SCOPE)[0]


def test_the_consistency_sample_can_rerun_a_relevance_ruling(tmp_path):
    _run(tmp_path, {"S003": CV.CHAPTER}, Lexical())
    rec = json.loads((tmp_path / "rulings" / "rulings.jsonl").read_text().splitlines()[0])
    assert rec["ruling_kind"] == "relevance" and tuple(rec["inputs"]) == R.RELEVANCE_FIELDS
    second, _u, note = CS.ruling_reask(Lexical())(rec)
    assert note is None and second["ruling"] == rec["ruling"]


def test_the_stage_cap_prices_relevance_rulings(tmp_path):
    d = tmp_path / "WHU-X01-x" / "rulings"
    d.mkdir(parents=True)
    (d / "rulings.jsonl").write_text(json.dumps({"ruling_kind": "relevance", "usage": {"usd": 0.01}}) + "\n" +
                                     json.dumps({"ruling_kind": "omission", "usage": {"usd": 0.09}}) + "\n")
    each, how = SC.per_unit("judgements", entries=[], issues_dir=tmp_path)
    assert each == pytest.approx(0.01) and "relevance" in how
    assert SC.per_unit("judgements", entries=[], issues_dir=tmp_path / "none")[0] == 0.02


def test_the_judgements_mode_is_capped_as_judgements(monkeypatch):
    seen = []

    class Stop(Exception):
        pass
    monkeypatch.setattr(R, "require_study", lambda slug, P=None: None)
    monkeypatch.setattr(R, "pending", lambda mode, slug, P=None: 5)
    monkeypatch.setattr(R, "unsampled", lambda log, cons, kind: [])
    monkeypatch.setattr(R, "log_path", lambda slug: Path("/nonexistent/rulings.jsonl"))
    monkeypatch.setattr(SC, "guard", lambda stage, slug, units: (seen.append(stage), (_ for _ in ()).throw(Stop())))
    with pytest.raises(Stop):
        R.main(["judgements", "x"])
    assert seen == ["judgements"]


# ----------------------------------------------------------------- replays

def test_replay_s08_and_s03_candidates():
    if not list((ROOT / "issues").glob("WHU-S08-*/bindings.json")):
        pytest.skip("the study's records are private and not here")
    h8 = R.held_texts("settlement-planning-climate-resilience")
    h3 = R.held_texts("public-involvement-climate-policy")
    if not h8 or not h3:
        pytest.skip("the held texts are not here")
    c8 = [c for c in J.candidates(h8) if c["kind"] == "assessment"]
    c3 = [c for c in J.candidates(h3) if c["kind"] == "assessment"]
    assert len(c8) == 9 and len(c3) == 19
    t = h3["S006"]
    i = t.find("a broad group of actors")
    assert [c["section"] for c in c3 if c["at"][0] <= i < c["at"][1]] == ["Executive Summary ¶7"]
