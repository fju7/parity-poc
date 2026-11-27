"""A model 'sentence' past its field limit takes the one-sentence path, never a run stop (P199, after WHU-OT1-04d:
the judgements step stopped on "field 'sentence' is over 1000 characters"). $0, offline."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import pytest  # noqa: E402
from orch import model_steps as M  # noqa: E402
from orch.steps import FIELD_LIMITS as F  # noqa: E402

LONG = "The assessment finds " + "with high confidence that removal matters, " * 40 + "in every pathway."
OK = "The assessment finds with high confidence that removal is needed to reach net zero."


class Ask:
    def __init__(self, replies):
        self.replies, self.prompts = list(replies), []

    def __call__(self, prompt, limit, role):
        self.prompts.append(prompt)
        return json.dumps(self.replies.pop(0))


def test_an_over_long_judgement_sentence_is_re_asked_then_accepted():
    assert len(LONG) > F["judgement.sentence"]
    ask = Ask([{"sentence": LONG}, {"sentence": OK}])
    assert M.judgement_sentence("held text", ask) == OK and len(ask.prompts) == 2


def test_an_over_long_judgement_sentence_twice_is_not_one_sentence():
    ask = Ask([{"sentence": LONG}, {"sentence": LONG}])
    with pytest.raises(M.NotOneSentence):            # the caller declares it (NOT_ADDED_NOT_ONE), never a stop
        M.judgement_sentence("held text", ask)


def test_an_over_long_coverage_sentence_is_re_asked_then_in_scope():
    ask = Ask([{"decision": "state", "why": "w", "sentence": LONG}, {"decision": "state", "why": "w", "sentence": LONG}])
    d = M.coverage_decision("q?", "scope", "unit", ask)
    assert d["decision"] == "in_scope" and "not one sentence" in d["why"]
    ask = Ask([{"decision": "state", "why": "w", "sentence": LONG}, {"decision": "state", "why": "w", "sentence": OK}])
    assert M.coverage_decision("q?", "scope", "unit", ask)["sentence"] == OK


def test_other_over_long_fields_still_stop():
    with pytest.raises(M.StepFailed):
        M._str({"why": "x" * 5000}, "why", 100)
