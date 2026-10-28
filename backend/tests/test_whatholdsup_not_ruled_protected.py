"""MERIT: not_ruled_protected -- an objection on a protected sentence, closed
without a merit verdict, accepted ONLY when the sentence is protected.

Post-study, mid-rerun tool fix (2026-10-28). Advocate and omission objections
aimed at a protected sentence (the question restatement, what we read or did not
read) are never ruled (ruling.split_protected) and wait for a person, who had no
way to close them except a merit verdict the protected sentence cannot take.

The adjudication file is written by the real source_advocate.write_template; the
real _closed, open_items, ruling.advocate_items and bindings.protected_kind decide.

COUNTERFACTUAL. Accept not_ruled_protected without the check (return True) and
t_unprotected goes red; drop the row lookup in protected_check (rows.get(...) ->
None) and t_row_marker goes red; drop the word from VERDICT and t_protected goes red.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import bindings as B                         # noqa: E402
import coverage_check as C                   # noqa: E402
import ruling as R                           # noqa: E402
import source_advocate as SA                 # noqa: E402
import test_whatholdsup_fix2_ruling as T     # noqa: E402

QUESTION = T.PAGE[0]          # "The question is whether ..." -- protected (question)
READING = T.PAGE[3]           # "We did not search the grey literature." -- protected (reading)
FINDING = T.PAGE[1]           # a finding: not protected


def _adj(tmp_path, monkeypatch, objs):
    adj = T._case(tmp_path, monkeypatch, objs)
    text = adj.read_text().replace("MERIT:  \n", "MERIT:  not_ruled_protected — a person: protected sentence\n")
    text = text.replace("OMISSION: \n", "MERIT:  not_ruled_protected\nOMISSION: \n")
    adj.write_text(text)
    return adj


def _misstates(anchor):
    return T._obj("Changes in layout could reduce emissions.", anchor=anchor, type_="MISSTATES")


def test_sanity_the_fixture_sentences():
    assert B.protected_kind(QUESTION) == "question" and B.protected_kind(READING) == "reading"
    assert B.protected_kind(FINDING) is None


def test_protected_sentence_closes(tmp_path, monkeypatch):
    adj = _adj(tmp_path, monkeypatch, [_misstates(QUESTION)])
    chunk = "### " + T._chunk(adj, "S003-01")
    assert SA._closed(chunk, "objections", SA.protected_check(T.SLUG))
    assert SA.open_items(T.SLUG) == ([], [])
    assert R.advocate_items(T.SLUG, tmp_path) == []


def test_unprotected_sentence_does_not_close(tmp_path, monkeypatch):
    adj = _adj(tmp_path, monkeypatch, [_misstates(FINDING)])
    chunk = "### " + T._chunk(adj, "S003-01")
    assert not SA._closed(chunk, "objections", SA.protected_check(T.SLUG))
    assert len(SA.open_items(T.SLUG)[0]) == 1
    assert len(R.advocate_items(T.SLUG, tmp_path)) == 1


def test_without_a_checker_it_does_not_close(tmp_path, monkeypatch):
    adj = _adj(tmp_path, monkeypatch, [_misstates(QUESTION)])
    assert not SA._closed("### " + T._chunk(adj, "S003-01"), "objections")


def test_row_marker_makes_a_sentence_protected(tmp_path, monkeypatch):
    _adj(tmp_path, monkeypatch, [_misstates(FINDING)])
    monkeypatch.setattr(B, "load", lambda slug: {"bindings": {
        B.fingerprint(FINDING): {"sentence": FINDING, "protected": "reading"}}})
    assert SA.open_items(T.SLUG) == ([], [])


def test_omission_objection_on_a_protected_sentence_closes(tmp_path, monkeypatch):
    _adj(tmp_path, monkeypatch, [T._obj(T.OMITTED, anchor=READING)])
    assert SA.open_items(T.SLUG) == ([], [])
    assert R._leaves_out(T.SLUG, tmp_path) == []


def test_for_the_study_log_not_the_readers_list(tmp_path, monkeypatch):
    import source_store
    _adj(tmp_path, monkeypatch, [_misstates(QUESTION), _misstates(FINDING)])
    assert [h.split(": ")[1] for h in SA.not_ruled_protected(T.SLUG)] == ["S003-01 — SERIOUS / NARROWS"]
    rows = {n: (s, d) for n, s, d in SA.preflight_rows(T.SLUG)}
    assert "study log" in rows["objections not ruled: protected sentence"][1]
    monkeypatch.setattr(source_store, "case_dir", lambda slug: tmp_path)
    assert C.declarations(T.SLUG, T.HELD, tmp_path) == []
