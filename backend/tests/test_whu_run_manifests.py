"""Run provenance manifests (advisor's ruling 2026-11-24): every run reported as a result has a committed manifest of
its bindings file and every held document (path, sha256, size, mtime); the files go to the private study folder,
never the public repo. $0: no model, no network."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
import orchestrator as O  # noqa: E402
import run_manifest as RM  # noqa: E402
import source_store as store  # noqa: E402


def test_every_run_reported_as_a_result_has_a_committed_manifest():
    """The standing check: the lean test's four runs and every orchestrated run whose run_paid.json says Ready."""
    assert RM.check() == []


def test_the_lean_test_runs_are_the_result_runs_named():
    slugs = {s for s, _c in RM.result_runs()}
    assert set(RM.LEAN_RESULT_RUNS) <= slugs


def _repo(tmp_path, ready=True, manifest=None, commit=True):
    root = tmp_path / "repo"
    case = root / "issues" / "WHU-OT1-99-whu-x"
    (case / "orchestrator").mkdir(parents=True)
    (case / "issue.json").write_text(json.dumps({"slug": "whu-x"}))
    (case / "orchestrator" / "run_paid.json").write_text(json.dumps({"result": "Ready." if ready else "Not Ready"}))
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    if manifest is not None:
        (case / RM.ORCH_MANIFEST).write_text(json.dumps(manifest))
        if commit:
            subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    return root


DOC = {"files": [{"role": "document", "source_id": "S001", "sha256": "a" * 64, "path": "library:docs/a.pdf"}]}


def test_a_ready_orchestrated_run_without_a_manifest_fails(tmp_path):
    root = _repo(tmp_path)
    assert RM.check(root) == ["whu-x: no manifest (issues/WHU-OT1-99-whu-x/orchestrator/provenance_manifest.json)"]


def test_an_uncommitted_manifest_fails(tmp_path):
    root = _repo(tmp_path, manifest=DOC, commit=False)
    assert RM.check(root)[0].startswith("whu-x: manifest not committed")


def test_a_manifest_changed_after_it_was_committed_fails(tmp_path):
    root = _repo(tmp_path, manifest=DOC)
    (root / "issues" / "WHU-OT1-99-whu-x" / RM.ORCH_MANIFEST).write_text(json.dumps({"files": []}))
    assert RM.check(root)[0].startswith("whu-x: manifest not committed")


def test_a_manifest_with_no_held_document_fails(tmp_path):
    root = _repo(tmp_path, manifest={"files": [{"role": "bindings", "sha256": "b" * 64}]})
    assert RM.check(root) == ["whu-x: manifest lists no held document"]


def test_a_committed_manifest_passes_and_a_not_ready_run_is_not_a_result(tmp_path):
    assert RM.check(_repo(tmp_path, manifest=DOC)) == []
    assert RM.check(_repo(tmp_path / "b", ready=False)) == []


def test_build_hashes_the_bindings_and_documents_and_copies_them_privately(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    lib = repo / "library"
    (lib / "docs" / "ab").mkdir(parents=True)
    (lib / "issues").mkdir()
    doc = lib / "docs" / "ab" / "ab12.pdf"
    doc.write_bytes(b"%PDF ZQX-HELD-BYTES-7731")
    blocked = lib / "docs" / "ab" / "ab34.xml"
    blocked.write_bytes(b"<xml>blocked</xml>")
    case = repo / "issues" / "WHU-OT1-98-whu-y"
    (case / "orchestrator").mkdir(parents=True)
    (case / "bindings.json").write_text('{"bindings": {}}')
    (case / "sources.json").write_text(json.dumps({"sources": [
        {"id": "S001", "access": {"state": "full_text_held"}},
        {"id": "S002", "access": {"state": "blocked", "not_held": {"line": "correction_unread", "why": "x"}}}]}))
    ix = lib / "issues" / "whu-y.json"
    ix.write_text(json.dumps({"sources": {"S001": {"file": "docs/ab/ab12.pdf"}, "S002": {"file": "docs/ab/ab34.xml"}}}))
    monkeypatch.setattr(store, "LIB", lib)
    monkeypatch.setattr(store, "CASES", repo / "issues")
    monkeypatch.setattr(RM, "ROOT", repo)
    monkeypatch.setenv("WHU_PRIVATE_ROOT", str(tmp_path / "private"))
    man = RM.build("whu-y")
    assert (case / RM.ORCH_MANIFEST).exists()
    by = {(f["role"], f.get("source_id")): f for f in man["files"]}
    assert by[("document", "S001")]["sha256"] == hashlib.sha256(b"%PDF ZQX-HELD-BYTES-7731").hexdigest()
    assert by[("document", "S001")]["size"] == len(b"%PDF ZQX-HELD-BYTES-7731") and by[("document", "S001")]["used"]
    assert by[("document", "S002")]["holding"] == "blocked" and by[("document", "S002")]["used"] is False
    assert {"bindings", "library_index"} <= {f["role"] for f in man["files"]}
    copy = tmp_path / "private" / "run_provenance" / "whu-y" / "library" / "docs" / "ab" / "ab12.pdf"
    assert copy.read_bytes() == b"%PDF ZQX-HELD-BYTES-7731" and man["copied"] == 4
    assert "ZQX-HELD-BYTES-7731" not in (case / RM.ORCH_MANIFEST).read_text()     # hashes and paths only


def test_the_private_copy_may_never_be_inside_the_public_repo(monkeypatch):
    monkeypatch.setenv("WHU_PRIVATE_ROOT", str(ROOT / "backend" / "data"))
    with pytest.raises(SystemExit, match="inside the public repo"):
        RM.build("whu-lean-q1-03b", copy=True)


def test_03b_s_bindings_changed_after_its_archive_and_the_manifest_says_so():
    """Q1-03b's bindings.json was rewritten after its 11:54Z archive by the recorded binding fix (9863fb2; de7fc35,
    "Q1-03b Ready again after the binding fix"): four readers'-list rows bound by code."""
    case = ROOT / "issues" / "WHU-L1-03b-whu-lean-q1-03b"
    man = json.loads((case / RM.MANIFEST).read_text(encoding="utf-8"))
    assert man["bindings_at_archive"]["sha256"].startswith("25a196ffb343")
    assert man["bindings_at_archive"]["matches_current"] is False


def test_the_orchestrator_records_a_manifest_failure_instead_of_hiding_it(monkeypatch):
    def boom(slug, copy=True):
        raise OSError("disk full")
    monkeypatch.setattr(RM, "build", boom)
    assert O.write_run_manifest("whu-x") == {"error": "OSError: disk full"}


def test_the_scored_bindings_are_marked_and_q1_03b_s_is_the_post_fix_version():
    """Established from timestamps and commits (deviations P076): Q1-03b was judged on a8a8f524 (written 16:07:11Z
    by the binding fix, before judging began at 16:11:30Z), not on the 11:54Z archive's 25a196ff."""
    for s in ("01c", "02b", "03b"):
        case = next((ROOT / "issues").glob("WHU-L1-%s-*" % s))
        man = json.loads((case / RM.MANIFEST).read_text(encoding="utf-8"))
        b = next(f for f in man["files"] if f["role"] == "bindings")
        assert man["scored_bindings"]["status"] == "scored" and b["scored"] is True
        assert man["scored_bindings"]["sha256"] == b["sha256"]
    m03 = json.loads((next((ROOT / "issues").glob("WHU-L1-03b-*")) / RM.MANIFEST).read_text(encoding="utf-8"))
    assert m03["scored_bindings"]["sha256"].startswith("a8a8f524")
    assert m03["bindings_at_archive"]["sha256"].startswith("25a196ff")
    m04 = json.loads((next((ROOT / "issues").glob("WHU-L1-04c-*")) / RM.MANIFEST).read_text(encoding="utf-8"))
    assert "scored_bindings" not in m04                    # Q1-04c was not scored
