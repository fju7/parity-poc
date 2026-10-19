"""When does the Signal source-verification job fail?

Rule (2026-10-19): only for what reaches a reader. A PUBLISHED topic is judged
by its publish record -- the record must exist, every source it lets survive
must have a held document, and the corpus must not have changed since. Draft
topics are not served, so their uncitable rows are reported but do not fail.
Offline: no Supabase, no network.
"""
import importlib.util
import json
import sys
from pathlib import Path

SIGNAL = Path(__file__).resolve().parents[2] / "scripts" / "signal"
sys.path.insert(0, str(SIGNAL))
_spec = importlib.util.spec_from_file_location("verify_sources", SIGNAL / "verify_sources.py")
vs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vs)

BACKEND = Path(__file__).resolve().parents[2]


def _record(tmp, slug, sources):
    d = tmp / "published" / slug
    d.mkdir(parents=True)
    (d / "latest.json").write_text(json.dumps({"sources": sources}))
    return tmp / "published"


def _held(tmp, name="doc.txt.gz"):
    p = tmp / "docs" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x")
    return str(p)  # absolute: (backend / abs) == abs


def _row(slug, i, verdict="NEVER_FETCHED"):
    return {"id": f"{slug}-{i}", "slug": slug, "verdict": verdict}


# --- published_problems ---------------------------------------------------------

def test_record_covering_the_corpus_is_clean(tmp_path):
    root = _record(tmp_path, "t", [
        {"source_id": "a", "survives": True, "document": {"path": _held(tmp_path)}},
        {"source_id": "b", "survives": False, "document": None},   # withheld: no doc needed
    ])
    assert vs.published_problems("t", {"a", "b"}, root=root) == []


def test_missing_record_fails(tmp_path):
    (tmp_path / "published").mkdir()
    probs = vs.published_problems("t", {"a"}, root=tmp_path / "published", backend=tmp_path)
    assert probs and "no publish record" in probs[0]


def test_surviving_source_without_held_document_fails(tmp_path):
    root = _record(tmp_path, "t", [
        {"source_id": "a", "survives": True,
         "document": {"path": str(tmp_path / "docs" / "gone.txt.gz")}},
    ])
    probs = vs.published_problems("t", {"a"}, root=root)
    assert len(probs) == 1 and "no held document" in probs[0]


def test_source_added_after_publishing_fails(tmp_path):
    root = _record(tmp_path, "t", [
        {"source_id": "a", "survives": True, "document": {"path": _held(tmp_path)}},
    ])
    probs = vs.published_problems("t", {"a", "new-source"}, root=root)
    assert len(probs) == 1 and "never gated" in probs[0]


def test_source_removed_after_publishing_fails(tmp_path):
    root = _record(tmp_path, "t", [
        {"source_id": "a", "survives": True, "document": {"path": _held(tmp_path)}},
        {"source_id": "b", "survives": True, "document": {"path": _held(tmp_path, "b.gz")}},
    ])
    probs = vs.published_problems("t", {"a"}, root=root)
    assert len(probs) == 1 and "no longer in the corpus" in probs[0]


def test_unreadable_record_fails(tmp_path):
    d = tmp_path / "published" / "t"
    d.mkdir(parents=True)
    (d / "latest.json").write_text("{not json")
    probs = vs.published_problems("t", {"a"}, root=tmp_path / "published")
    assert probs and "unreadable" in probs[0]


# --- report(): the exit rule -----------------------------------------------------

def test_drafts_only_failures_pass_but_are_reported(tmp_path, capsys):
    root = _record(tmp_path, "pub", [
        {"source_id": "pub-1", "survives": True, "document": {"path": _held(tmp_path)}},
    ])
    rows = [_row("pub", 1), _row("draft", 1), _row("draft", 2)]
    bad = rows[:]  # the corpus-row check calls every one of them uncitable
    code, outcome = vs.report(bad, bad, {"pub"}, rows, root=root)
    out = capsys.readouterr().out
    assert (code, outcome) == (0, "drafts_only")
    assert "DRAFT TOPICS (not served): 2 of 2" in out
    assert "pub: ok" in out


def test_a_published_problem_fails_even_if_drafts_are_fine(tmp_path, capsys):
    (tmp_path / "published").mkdir()
    rows = [_row("pub", 1, "OK"), _row("draft", 1, "OK")]
    code, outcome = vs.report(rows, [], {"pub"}, rows, root=tmp_path / "published")
    assert (code, outcome) == (1, "published_problem")
    assert "pub: FAIL" in capsys.readouterr().out


def test_published_topic_with_no_corpus_rows_left_fails(tmp_path, capsys):
    root = _record(tmp_path, "pub", [
        {"source_id": "pub-1", "survives": True, "document": {"path": _held(tmp_path)}},
    ])
    code, outcome = vs.report([], [], {"pub"}, [], root=root)
    assert (code, outcome) == (1, "published_problem")


def test_everything_clean_passes(tmp_path):
    root = _record(tmp_path, "pub", [
        {"source_id": "pub-1", "survives": True, "document": {"path": _held(tmp_path)}},
    ])
    rows = [_row("pub", 1, "OK")]
    assert vs.report(rows, [], {"pub"}, rows, root=root) == (0, "clean")


# --- the real record ---------------------------------------------------------------

def test_the_real_mmr_record_covers_its_surviving_sources():
    rec = json.loads((vs.PUBLISHED / "mmr-vaccine-autism" / "latest.json").read_text())
    ids = {s["source_id"] for s in rec["sources"]}
    assert vs.published_problems("mmr-vaccine-autism", ids) == []
    assert sum(1 for s in rec["sources"] if s["survives"]) == 34
