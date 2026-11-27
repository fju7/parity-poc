"""An orchestrated omission ADD with no citation marker gets its own source's (P211, after WHU-OT1-04g: an ADD ending
'... methods."' with no marker merged with the next sentence under the audit's splitter and applied_check stopped
the run at omissions). $0, offline."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import applied_check as AC  # noqa: E402
import ruling as R  # noqa: E402

TEXT = ('The IPCC assessment finds, with high confidence, that "afforestation, reforestation, improved forest '
        'management, agroforestry and soil carbon sequestration are currently the only widely practiced CDR methods."')
NEXT = "In model pathways, global net CO2 emissions reach net zero around 2050 [3]."


def _case(tmp_path):
    (tmp_path / "sources.json").write_text(json.dumps({"sources": [{"id": "S001"}, {"id": "S002"}, {"id": "S003"}]}))
    return tmp_path


def test_orchestrated_add_without_a_marker_gets_its_sources(tmp_path, monkeypatch):
    monkeypatch.setenv("WHU_ORCH_STEP", "omissions")
    got = R.orchestrated_marker(_case(tmp_path), "S002", TEXT)
    assert got.endswith('CDR methods" [2].')
    page = "<p>%s %s</p>" % (got, NEXT)
    assert AC.page_sentences(page) == [got, NEXT]                # two units, as the audit splits them
    before = AC.page_sentences("<p>%s %s</p>" % (TEXT, NEXT))
    assert len(before) == 1                                        # the defect: one unit


def test_a_marker_already_there_or_outside_an_orchestrated_run_is_unchanged(tmp_path, monkeypatch):
    marked = "Removal grows over time [1]."
    monkeypatch.setenv("WHU_ORCH_STEP", "omissions")
    assert R.orchestrated_marker(_case(tmp_path), "S001", marked) == marked
    assert R.orchestrated_marker(_case(tmp_path), "S009", TEXT) == TEXT        # a source not listed: unchanged
    monkeypatch.delenv("WHU_ORCH_STEP")
    assert R.orchestrated_marker(_case(tmp_path), "S002", TEXT) == TEXT


def test_the_omission_ruling_marks_the_add_before_recording_it():
    src = (ROOT / "backend/scripts/whatholdsup/ruling.py").read_text(encoding="utf-8")
    i = src.index('got["text"] = orchestrated_marker(case, f["source"], got["text"])')
    assert i < src.index("on_page=B.fingerprint(got[\"text\"])", i)
