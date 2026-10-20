"""A reader quotation still not word for word after its re-read (2026-10-20).

The rejected quotation is logged raw -- sentence id, document id, the reader's
own words -- in the run's private log (quote_rejections.jsonl, excluded from
git). The sentence is marked FAILED_READ and the run continues; at the end of
the run it becomes HUMAN_READ_REQUIRED. Until now one such sentence stopped the
whole run.
"""
import importlib.util
import json
import re
import subprocess
from pathlib import Path

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
spec = importlib.util.spec_from_file_location("audit_stage_failed_read_t", WHU / "audit_stage.py")
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)

DOC = ("Of 795 colonoscopies before AI was introduced, 226 detected an adenoma (28.4%). "
       "After introduction, 145 of 648 did (22.4%).")
HELD = {"demo:S021": DOC}


def _unit(uid, sentence, sid="S021", span="226 detected an adenoma (28.4%)"):
    return {"id": uid, "part": "page", "sentence": sentence, "sha": A.fingerprint(sentence),
            "row": {"source_id": sid, "span": span}}

GOOD = "226 detected an adenoma (28.4%)"
BAD = "226 detected adenomas in 28.4 per cent"                 # not in the document


class OneBadQuoter:
    """u1 always quotes text that is not in the document; u2 quotes it exactly."""

    def __init__(self):
        self.prompts = []

    def __call__(self, prompt, max_tokens):
        self.prompts.append(prompt)
        ids = re.findall(r"^\[(u\d+)\]", prompt, re.M)
        out = {"verdicts": [{"id": i, "verdict": "holds", "kind": None,
                             "evidence": [{"source": "S021", "quote": BAD if i == "u1" else GOOD}],
                             "proposed_text": None, "reason": "test"} for i in ids]}
        return json.dumps(out), {"input": 1, "output": 1, "usd": 0.0}


def _run(tmp_path):
    us = [_unit("u1", "Of 795 colonoscopies, 226 detected an adenoma."),
          _unit("u2", "Of 795 colonoscopies, 226 detected an adenoma (28.4%).")]
    return us, A.run("demo", out_dir=tmp_path, ask=OneBadQuoter(), held=HELD, unit_list=us, cap=1.0,
                     licensed=set())


def test_one_failing_sentence_does_not_stop_the_others_and_ends_as_human_read_required(tmp_path):
    us, m = _run(tmp_path)
    assert m["status"] == "complete", m.get("failure")
    assert m["state"][us[0]["sha"]] == A.HUMAN_READ_REQUIRED
    assert m["state"][us[1]["sha"]] == "holds"
    assert m["failed_read"] == [{"unit": "u1", "sha": us[0]["sha"]}]
    # and the preflight then blocks until a person reads it
    row = A.preflight_rows("demo", [], current=us, run_dir=tmp_path)[0]
    assert row[1] == A.BAD and "no recorded human read" in row[2]


def test_every_rejected_quotation_is_logged_raw_with_its_sentence_and_document(tmp_path):
    _run(tmp_path)
    recs = [json.loads(l) for l in (tmp_path / "quote_rejections.jsonl").read_text().splitlines()]
    assert [(r["unit"], r["attempt"], r["source"], r["quote"]) for r in recs] == \
        [("u1", "first read", "S021", BAD), ("u1", "re-read", "S021", BAD)]


def test_the_rejection_log_is_excluded_from_git():
    root = WHU.parents[2]
    for p in ("issues/WHU-003-deskilling/audit/20261020T000000Z/quote_rejections.jsonl",
              "issues/WHU-P02-ultra-processed-foods/audit/20261020T000000Z/quote_rejections.jsonl"):
        assert subprocess.run(["git", "-C", str(root), "check-ignore", "-q", "--no-index", p]).returncode == 0, p
