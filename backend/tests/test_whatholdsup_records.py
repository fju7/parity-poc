"""B24: a sentence may rest on WHU's own committed records (rests_on_record),
and B19 reads 'plausibly' / 'plausible' as hedges. 2026-10-18. Fixtures only:
git is never called; `_committed` is replaced by a dict of committed files."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, WHU / ("%s.py" % name))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(WHU))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


B = _load("bindings")
CASE = "issues/WHU-099-test"
RULING = CASE + "/review/2026-09-12-ruling.md"
QUOTE = 'A "Last reviewed" date on a page is a currency claim'


@pytest.fixture
def repo(monkeypatch):
    files = {RULING: ("a" * 40, "# Ruling\n\nA \"Last reviewed\" date on a page\nis a currency claim, and we withdraw it.\n")}
    monkeypatch.setattr(B, "_committed", lambda p: files.get(p))
    monkeypatch.setattr(B.store, "case_dir", lambda slug: B._repo_root() / CASE)
    return files


def row(**kw):
    r = {"sentence": "Both of those are true, and in our judgement neither is what a reader takes "
                     "from a review date on a page.", "on_page": True, "bucket": "deterministic",
         "rests_on_record": [{"path": RULING, "quote": QUOTE, "sha": "a" * 40}]}
    r.update(kw)
    return r


def verdicts(r):
    return [f["verdict"] for f in B.b24_records(r, "t")]


def test_found_a_quote_in_the_committed_file_is_clean_across_a_line_break(repo):
    assert verdicts(row()) == [] and B.record_bound(row(), "t")


def test_changed_the_file_moved_on_with_the_quote_intact_warns(repo):
    repo[RULING] = ("b" * 40, repo[RULING][1] + "\nAn added paragraph.\n")
    assert verdicts(row()) == [B.RECORD_CHANGED]
    assert B.CALIBRATION_SEVERITY[B.RECORD_CHANGED] == B.WARN
    assert B.record_bound(row(), "t"), "a changed record that still says it is still support"


def test_missing_the_quote_is_gone_blocks(repo):
    repo[RULING] = ("c" * 40, "# Ruling\n\nWithdrawn.\n")
    assert verdicts(row()) == [B.RECORD_GONE]
    assert B.CALIBRATION_SEVERITY[B.RECORD_GONE] == B.BAD
    assert not B.record_bound(row(), "t")


def test_missing_a_file_not_committed_blocks(repo):
    del repo[RULING]
    assert verdicts(row()) == [B.RECORD_GONE]


@pytest.mark.parametrize("path", ["site/whatholdsup/deskilling.html", "/etc/passwd",
                                  CASE + "/../WHU-001/corrections.md", "issues/WHU-001-other/corrections.md"])
def test_a_path_outside_docs_and_the_case_directory_is_refused(repo, path):
    r = row(rests_on_record=[{"path": path, "quote": QUOTE, "sha": "a" * 40}])
    assert verdicts(r) == [B.RECORD_REFUSED]


def test_a_binding_with_no_sha_is_incomplete(repo):
    r = row(rests_on_record=[{"path": RULING, "quote": QUOTE}])
    assert verdicts(r) == [B.RECORD_INCOMPLETE]


def test_record_entry_writes_the_sha_it_checked_and_refuses_a_missing_quote(repo):
    assert B.record_entry(RULING, QUOTE, "t") == {"path": RULING, "quote": QUOTE, "sha": "a" * 40}
    with pytest.raises(ValueError):
        B.record_entry(RULING, "a sentence the ruling does not contain", "t")
    with pytest.raises(ValueError):
        B.record_entry("site/x.html", QUOTE, "t")


def test_docs_is_a_record_location(repo):
    repo["docs/whatholdsup-deskilling-revision.md"] = ("d" * 40, "We read it.")
    r = row(rests_on_record=[{"path": "docs/whatholdsup-deskilling-revision.md", "quote": "We read it.",
                              "sha": "d" * 40}])
    assert verdicts(r) == []


def test_b21_does_not_ask_the_store_about_a_record_bound_process_claim(repo, monkeypatch):
    r = row(sentence="We have not been able to read the full text.", trigger=B.PROCESS_TRIGGER)
    assert B.b21_holdings(r, "t") == []


def test_b21_still_refuses_a_document_as_support_on_a_record_bound_row(repo, monkeypatch):
    sys.path.insert(0, str(WHU))
    import epistemic as E
    monkeypatch.setattr(E, "_sources", lambda slug: [])
    monkeypatch.setattr(E, "resolve", lambda s, g: [])
    r = row(sentence="We hold the paper.", source_id="S001", span="x")
    assert "holdings sentence cites a document" in [f["verdict"] for f in B.b21_holdings(r, "t")]


# --- B19: plausibly / plausible ------------------------------------------

def test_plausibly_in_the_sentence_is_a_hedge():
    r = {"sentence": "The population being examined plausibly changed.", "bucket": "judgement",
         "premises": [{"source_id": "S021", "span": "the compared patient cohorts might not have "
                                                     "comparable background characteristics"}]}
    assert B.b19_hedge_dropped(r) == []
    assert B.b19_hedge_dropped(dict(r, sentence="The population being examined changed."))


def test_plausible_in_the_evidence_is_a_hedge():
    r = {"sentence": "Gaze is the mechanism.", "span": "a plausible mechanism is gaze", "source_id": "S031"}
    assert [f["hedge"] for f in B.b19_hedge_dropped(r)] == ["plausible"]
