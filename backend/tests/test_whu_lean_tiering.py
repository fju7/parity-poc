"""Lean WHU model tiering for the judgement rulings (ruling.rule_judgements, escalate=).

No model is called. The smaller model is a fake that always says "not
relevant" (or always relevant); the current model is the fix-3 test's lexical
fake. Which model decided each candidate is read back from the records."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import judgements as J                          # noqa: E402
import lean                                     # noqa: E402
import ruling as R                              # noqa: E402
import test_whatholdsup_fix2_coverage as CV     # noqa: E402
import test_whatholdsup_fix3_judgements as F3   # noqa: E402


class Model:
    """A fake caller that knows its model, as audit_stage.Caller does."""

    def __init__(self, model, inner):
        self.model, self.inner, self.n = model, inner, 0

    def __call__(self, prompt, max_tokens, role):
        self.n += 1
        return self.inner(prompt, max_tokens, role)


def _never(prompt, max_tokens, role):
    return json.dumps({"relevant": False, "question_words": "", "reason": "small says no"}), {"usd": 0.0}


def _rulings(case):
    return [json.loads(l) for l in (case / "rulings" / "rulings.jsonl").read_text().splitlines()]


def test_a_not_relevant_from_the_smaller_model_is_ruled_again_by_the_current_model(tmp_path):
    small = Model(lean.SMALL, _never)
    big = Model(lean.CURRENT, F3.Lexical())
    done = R.rule_judgements("x", small, P=F3.P, held={"S003": CV.CHAPTER}, scope=F3.SCOPE,
                             case=tmp_path, escalate=big)
    assert done and small.n == len(done) == big.n
    recs = _rulings(tmp_path)
    assert {r["model"] for r in recs} == {lean.SMALL, lean.CURRENT}
    assert all(r.get("escalated_from") == lean.SMALL for r in recs if r["model"] == lean.CURRENT)
    cands = J.load(tmp_path)["candidates"]
    assert all(c["by"] == R.BY for c in cands.values())              # the current model decided each


def test_a_verified_relevant_from_the_smaller_model_stands(tmp_path):
    small = Model(lean.SMALL, F3.Lexical())
    big = Model(lean.CURRENT, _never)
    done = R.rule_judgements("x", small, P=F3.P, held={"S003": CV.CHAPTER}, scope=F3.SCOPE,
                             case=tmp_path, escalate=big)
    relevant = [d for d in done if d.get("relevant")]
    assert relevant
    cands = J.load(tmp_path)["candidates"]
    assert [c["by"] for c in cands.values() if c["relevant"]] == ["ruling model %s" % lean.SMALL] * len(relevant)
    assert big.n == len(done) - len(relevant)                         # only the rest were escalated


def test_without_lean_the_ruling_record_names_the_current_model(tmp_path):
    done = F3._run(tmp_path, {"S003": CV.CHAPTER}, F3.Lexical())
    assert done and {r["model"] for r in _rulings(tmp_path)} == {R.MODEL}
    assert {r["by"] for r in _rulings(tmp_path)} == {R.BY}
