"""Fix 2, step 6: an inserted sentence is checked as applied (post-study, 2026-10-27).

The ADD decision and its ruling record are made by the real omission ruling
(ruling.rule_omissions, with a fake model answering from its prompt); this
file then applies them to a page, correctly and incorrectly, and asks
applied_check.
"""
import importlib.util
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import bindings as B                     # noqa: E402
import omissions as O                    # noqa: E402
import ruling as R                       # noqa: E402
import test_whatholdsup_fix2_ruling as T  # noqa: E402

spec = importlib.util.spec_from_file_location("applied_check_fix2_t", WHU / "applied_check.py")
AC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(AC)


def page(sentences):
    return "<html><body>%s</body></html>" % "".join("<p>%s</p>" % s for s in sentences)


def _decide(tmp_path, monkeypatch, reply=None, objections=None):
    T._case(tmp_path, monkeypatch, objections or [T._obj(T.OMITTED)])
    [d] = T._run(tmp_path, T.Fake(reply or T.ADD))
    return d


def test_an_insert_directly_after_its_anchor_is_applied(tmp_path, monkeypatch):
    d = _decide(tmp_path, monkeypatch)
    sents = T.PAGE[:2] + [d["text"]] + T.PAGE[2:]
    res = AC.check(tmp_path, page(sents))
    assert res["mismatches"] == [] and len(res["inserted"]) == 1


def test_an_insert_missing_or_misplaced_is_a_mismatch(tmp_path, monkeypatch):
    d = _decide(tmp_path, monkeypatch)
    res = AC.check(tmp_path, page(T.PAGE))
    assert len(res["mismatches"]) == 1 and res["mismatches"][0]["missing"]
    elsewhere = T.PAGE[:3] + [d["text"]] + T.PAGE[3:]
    [m] = AC.check(tmp_path, page(elsewhere))["mismatches"]
    assert m.get("misplaced")
    changed = T.PAGE[:2] + [d["text"].replace("further", "")] + T.PAGE[2:]
    assert AC.check(tmp_path, page(changed))["mismatches"]


def test_a_later_ruling_on_the_inserted_text_supersedes_it(tmp_path, monkeypatch):
    d = _decide(tmp_path, monkeypatch)
    later = "The assessment finds, with high confidence, that investment in public transport supports mode shift."
    with open(tmp_path / "rulings" / "rulings.jsonl", "a") as f:
        f.write(json.dumps({"at": "2099-01-01T00:00:00+00:00", "ruling_kind": "conclusion", "ruling": "amend",
                            "text": later, "inputs": {"sentence": d["text"]}}) + "\n")
    res = AC.check(tmp_path, page(T.PAGE[:2] + [later] + T.PAGE[2:]))
    assert res["mismatches"] == [] and any(s.get("ruling_kind") == "omission" for s in res["superseded"])


def test_an_add_refused_by_code_expects_nothing(tmp_path, monkeypatch):
    d = _decide(tmp_path, monkeypatch, reply=dict(T.ADD, span="Not in the finding at all.", draft_text="X."))
    assert d["outcome"] == O.TO_PERSON
    res = AC.check(tmp_path, page(T.PAGE))
    assert res["mismatches"] == [] and res["inserted"] == []


def test_dangling_sees_an_acronym_the_insert_brings_in(tmp_path, monkeypatch):
    reply = dict(T.ADD)
    d = _decide(tmp_path, monkeypatch, reply=reply)
    text = d["text"].replace("The assessment finds", "The SPM finds")
    entries = json.loads((tmp_path / O.RECORD).read_text())
    log = tmp_path / "rulings" / "rulings.jsonl"
    recs = [json.loads(l) for l in log.read_text().splitlines()]
    recs[-1]["text"] = text
    log.write_text("".join(json.dumps(r) + "\n" for r in recs))
    found = AC.dangling(tmp_path, page(T.PAGE[:2] + [text] + T.PAGE[2:]))
    assert [(f["term"], f["later_sentence"]) for f in found] == [("SPM", text)]
    # introduced earlier on the page: nothing dangles
    intro = ["The Summary for Policymakers (SPM) is the assessment's summary."] + T.PAGE[:2] + [text] + T.PAGE[2:]
    assert AC.dangling(tmp_path, page(intro)) == []
