"""The contrarianism guard is SKIPPED on a study issue (protocol rev 27).

The guard asks whether WHU picks subjects for the answer. A study question is
chosen by the protocol, not by WHU, so on a study issue the cross-issue guard is
SKIPPED -- on the premise board (premise.py status) and in the preflight, which
reads the same rows. A published issue's guard is unchanged.
"""
import importlib.util
import json
import sys
from pathlib import Path

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
spec = importlib.util.spec_from_file_location("premise_guard_t", WHU / "premise.py")
PR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PR)

SKIP = "SKIPPED — the study's questions are chosen by the protocol, not by WHU (protocol rev 27)"


def _case(root, name, slug, study):
    d = root / name
    d.mkdir(parents=True)
    (d / "issue.json").write_text(json.dumps({"slug": slug, "study": study}))
    (d / "premise.json").write_text(json.dumps({"direction": {"value": "corrects"}}))
    return d


def _guard(rows):
    return [r for r in rows if r[0] == "contrarianism guard"][0]


def test_the_guard_is_skipped_on_a_study_issue_and_not_on_a_published_one(tmp_path, monkeypatch):
    monkeypatch.setattr(PR, "CASES", tmp_path)
    _case(tmp_path, "WHU-P77-studyq", "studyq", True)
    _case(tmp_path, "WHU-077-pubq", "pubq", False)
    assert _guard(PR.preflight_rows("studyq")) == ("contrarianism guard", PR.OK, SKIP)
    _l, st, detail = _guard(PR.preflight_rows("pubq"))
    assert "SKIPPED" not in detail and (st, detail) == PR.contrarianism_guard()
