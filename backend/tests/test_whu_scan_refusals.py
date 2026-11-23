"""Advisor's ruling 4 (2026-11-23): the weekly lead scan never re-adds a refused identifier, and it skips trial,
seeded-defect and locked folders. Case: WHU-S06 S002's reference-list DOI, refused 26 Oct, re-added by the
scan on 26 Oct and again on 2 Nov."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
import sweep_sources as SS  # noqa: E402

spec = importlib.util.spec_from_file_location("scan_skip", W / "schedule" / "scan_skip.py")
SK = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SK)

S06 = "issues/WHU-S06-arts-youth-offending/sources.json"
DOI = "10.1016/j.tsc.2018.06.003"


def _s06_committed() -> str:
    return subprocess.run(["git", "show", "HEAD:" + S06], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout


def _case(tmp_path):
    d = tmp_path / "issues" / "WHU-S06-arts-youth-offending"
    d.mkdir(parents=True)
    (d / "sources.json").write_text(_s06_committed(), encoding="utf-8")
    return d


def test_s06_record_names_the_refused_doi():
    s002 = next(r for r in json.loads(_s06_committed())["sources"] if r["id"] == "S002")
    assert DOI in SS.refused_values(s002)
    assert "identifier" not in s002                    # the committed record carries no identifier for S002


def test_a_refused_identifier_is_never_written(tmp_path):
    d = _case(tmp_path)
    with pytest.raises(SystemExit, match="refused"):
        SS.write_identifier(d, "S002", {"kind": "doi", "value": DOI.upper()})
    s002 = next(r for r in json.loads((d / "sources.json").read_text())["sources"] if r["id"] == "S002")
    assert "identifier" not in s002


def test_resolve_write_skips_the_refused_candidate_without_a_lookup(tmp_path, monkeypatch, capsys):
    d = _case(tmp_path)
    monkeypatch.setattr(SS, "ISSUES", tmp_path / "issues")
    looked_up = []

    def resolve(cand, src):
        looked_up.append((src["id"], cand["value"]))
        return None, "stub: not resolved"
    monkeypatch.setattr(SS, "resolve_candidate", resolve)
    real = SS.candidate_shapes
    monkeypatch.setattr(SS, "candidate_shapes", lambda src, slug: (
        [{"kind": "doi", "value": DOI, "shape": "DOI read out of the document we hold"}] if src["id"] == "S002"
        else real(src, slug)))
    SS.cmd_resolve(SimpleNamespace(slug="arts-youth-offending", write=True))
    assert ("S002", DOI) not in looked_up
    s002 = next(r for r in json.loads((d / "sources.json").read_text())["sources"] if r["id"] == "S002")
    assert "identifier" not in s002


@pytest.mark.parametrize("name,skipped", [("WHU-OT1-02k-whu-lean-orch-t1-q1-02k", True), ("WHU-SD-01-x", True),
                                          ("WHU-S06-arts-youth-offending", False), ("WHU-001-melanoma", False)])
def test_scan_skips_trial_and_seeded_defect_folders(tmp_path, name, skipped):
    d = tmp_path / name
    d.mkdir()
    assert bool(SK.skip(d, lock=tmp_path / "no.lock")) is skipped


def test_scan_skips_the_folder_an_orchestrator_lock_names(tmp_path):
    d = tmp_path / "WHU-Q9-01-some-issue"
    d.mkdir()
    (d / "issue.json").write_text(json.dumps({"slug": "some-issue"}))
    lock = tmp_path / "orchestrator.lock"
    lock.write_text(json.dumps({"token": "t", "slug": "some-issue", "step": "audit"}))
    assert "orchestrator lock" in SK.skip(d, lock=lock)
    lock.write_text(json.dumps({"token": "t", "slug": "another"}))
    assert SK.skip(d, lock=lock) is None


def test_run_scan_calls_the_skip_before_any_sweep():
    sh = (W / "schedule" / "run_scan.sh").read_text()
    loop = sh[sh.index('for SRC in "$REPO"/issues/*/sources.json'):]
    assert loop.index("scan_skip.py") < loop.index("sweep_sources.py")
    r = subprocess.run(["/usr/bin/python3", str(W / "schedule" / "scan_skip.py"),
                        str(ROOT / "issues" / "WHU-OT1-02k-whu-lean-orch-t1-q1-02k")], capture_output=True, text=True)
    assert r.returncode == 0 and "WHU-OT1-" in r.stdout
