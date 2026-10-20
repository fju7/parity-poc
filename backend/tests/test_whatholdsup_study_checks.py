"""The two RUN.md checking scripts (study rulings 1 and 5, 2026-10-20).

applied_check (5a): every accepted ruling is on the page word for word,
normalised only as changecheck normalises. changecheck_coverage (9a): every
body sentence changed since the first full draft is in changecheck's read set.
Synthetic issues only.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))


def _load(name):
    spec = importlib.util.spec_from_file_location(name + "_sc_t", WHU / ("%s.py" % name))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


AC = _load("applied_check")
CV = _load("changecheck_coverage")
import changecheck as C  # noqa: E402

OLD = "The trial proved that the diet cut weight by 2 kg."
NEW = "The trial found that the diet cut weight by 2 kg in 12 weeks."


def page(*sentences):
    return ("<html><body><p>An opening sentence stands here.</p><p>%s</p>"
            "<p>Diets differ in many ways.</p></body></html>" % " ".join(sentences))


def ruling(case, text, ruled_on=OLD, kind="conclusion", at="2026-10-21T10:00:00+00:00", log="rulings/rulings.jsonl",
           **extra):
    p = case / log
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {"at": at, "by": "ruling model claude-opus-5-5", "ruling_kind": kind, "ruling": "amend",
           "text": text, "inputs": {"sentence": ruled_on}, **extra}
    with open(p, "a") as f:
        f.write(json.dumps(rec) + "\n")


# --- 5a: the ruling-application check ----------------------------------------

def test_an_exact_match_passes(tmp_path):
    ruling(tmp_path, NEW)
    res = AC.check(tmp_path, page("Intro sentence here.", NEW))
    assert res["mismatches"] == [] and len(res["checked"]) == 1


def test_whitespace_is_normalised_as_changecheck_normalises_and_nothing_else(tmp_path):
    ruling(tmp_path, NEW)
    spaced = NEW.replace(" found ", "\n   found ")
    assert AC.check(tmp_path, page(spaced))["mismatches"] == []
    # a changed word is not normalised away
    ruling(tmp_path / "b", NEW)
    assert len(AC.check(tmp_path / "b", page(NEW.replace("found", "showed")))["mismatches"]) == 1


def test_a_mismatch_fails(tmp_path):
    ruling(tmp_path, NEW)
    res = AC.check(tmp_path, page(OLD))                       # not applied
    assert len(res["mismatches"]) == 1 and res["mismatches"][0]["missing"] == [NEW]


def test_a_cut_is_applied_only_when_the_sentence_is_gone(tmp_path):
    ruling(tmp_path, "")
    assert len(AC.check(tmp_path, page(OLD))["mismatches"]) == 1
    assert AC.check(tmp_path, page("Something else."))["mismatches"] == []


def test_a_superseded_ruling_is_not_expected_only_the_last_text_is(tmp_path):
    ruling(tmp_path, NEW, kind="gate", at="2026-10-21T10:00:00+00:00")
    final = "The trial found a 2 kg loss in 12 weeks."
    ruling(tmp_path, final, ruled_on=NEW, at="2026-10-22T10:00:00+00:00",
           log="audit/20261022T100000Z/rulings.jsonl")
    res = AC.check(tmp_path, page(final))
    assert res["mismatches"] == [] and len(res["superseded"]) == 1 and len(res["checked"]) == 1


def test_a_rejection_expects_nothing_and_a_left_for_person_wording_is_skipped(tmp_path):
    ruling(tmp_path, None, ruling="reject")
    ruling(tmp_path, "A card wording.", apply=False, log="audit/r1/rulings.jsonl")
    res = AC.check(tmp_path, page(OLD))
    assert res["mismatches"] == [] and len(res["skipped"]) == 1 and res["checked"] == []


# --- 9a: the changecheck coverage check ---------------------------------------

def reviews(*runs):
    return {"reviews": [dict(r) for r in runs]}


def test_every_changed_sentence_read_passes():
    first, now = page(OLD), page(NEW)
    sent, _ = C.changed(first, now)
    res = CV.check(first, now, reviews({"read": [C.fingerprint(s) for s in sent], "model_read": True}))
    assert res["missed"] == [] and res["changed"] == 1


def test_an_unread_changed_sentence_fails():
    first = page(OLD)
    now = page(NEW, "A second new sentence was added.")
    res = CV.check(first, now, reviews({"read": [C.fingerprint(NEW)], "model_read": True}))
    assert res["missed"] == ["A second new sentence was added."]


def test_the_read_set_is_the_union_across_runs_and_a_blind_run_counts_for_nothing():
    first = page(OLD)
    now = page(NEW, "A second new sentence was added.")
    runs = reviews({"read": [C.fingerprint(NEW)], "model_read": True},
                   {"read": [C.fingerprint("A second new sentence was added.")], "model_read": False},
                   {"changed": 3})                                    # before `read` existed
    res = CV.check(first, now, runs)
    assert res["missed"] == ["A second new sentence was added."] and res["runs_without_a_read_set"] == 2
    runs["reviews"].append({"read": [C.fingerprint("A second new sentence was added.")], "model_read": True})
    assert CV.check(first, now, runs)["missed"] == []


def test_changecheck_records_what_it_read(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "record_path", lambda slug: tmp_path / "change-reviews.json")
    C.save_review("x", page(NEW), "abc", 1, [], [], read=[NEW], model_read=True)
    r = json.loads((tmp_path / "change-reviews.json").read_text())["reviews"][0]
    assert r["read"] == [C.fingerprint(NEW)] and r["model_read"] is True and NEW not in json.dumps(r)
