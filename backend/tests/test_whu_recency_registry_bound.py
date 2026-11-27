"""'A newer edition exists' rests on a registry record or a held newer work, never on the gate's web search alone
(advisor's ruling 2 on P171-P176, 2026-11-27). $0, offline."""
import glob
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import lean_editions as LE  # noqa: E402

STUDY = {"name": "Kuper H, Saran A, White H. Rapid Evidence Assessment 2018", "status": "SUPERSEDED",
         "latest_known": "functionally superseded by the 2025 Hunt et al. systematic review",
         "searched": ["Europe PMC", "Crossref", "the publisher's site"]}
SRCS = [{"id": "S003", "title": "Rapid Evidence Assessment of interventions for children with disabilities",
         "edition": "2018 report"}]


def _errata(case: Path, sid: str, amendments: list) -> None:
    (case / "errata.json").write_text(json.dumps({"checked": {sid: {"amendments": amendments}}}))


def test_gate_search_alone_gives_the_could_not_establish_wording(tmp_path):
    d = LE.decide("x", tmp_path, STUDY, "S003", SRCS, {}, {"S003": "text"}, matched_by="identifier (url)")
    assert d["outcome"] == LE.UNKNOWN_LINE and d["downgraded_from"] == LE.SUPERSEDED
    assert d["sentence"] == ("Our recency check (searched: Europe PMC, Crossref, the publisher's site) could not "
                             "establish whether Rapid Evidence Assessment of interventions for children with "
                             "disabilities has a newer edition.")
    assert not d["sentence"].startswith("A newer edition exists")
    assert "Hunt" not in d["sentence"]                                  # the gate's prose never reaches the page


@pytest.mark.parametrize("amend", [
    {"type": "Update in", "id": "40123456", "source": "MED"},                       # Europe PMC / PubMed
    {"type": "is-replaced-by", "id": "10.1002/cl2.9999", "source": "Crossref relation"},
    {"type": "new_edition", "id": "10.1002/cl2.9998", "source": "Crossref updated-by"},
])
def test_a_registry_record_of_the_newer_edition_allows_the_line(tmp_path, amend):
    _errata(tmp_path, "S003", [amend])
    d = LE.decide("x", tmp_path, STUDY, "S003", SRCS, {}, {"S003": "text"}, matched_by="identifier (url)")
    assert d["outcome"] == LE.DISCLOSED and d["sentence"].startswith("A newer edition exists of ")
    assert d["evidence"] == {"kind": "registry record", "records": [amend]}


@pytest.mark.parametrize("kind", ["Erratum in", "correction", "Corrected and republished in"])
def test_a_correction_is_not_a_newer_edition(tmp_path, kind):
    """Six of the nine recorded DISCLOSED lines rested on a corrigendum the gate called a newer edition."""
    _errata(tmp_path, "S003", [{"type": kind, "id": "37133285", "source": "MED"}])
    d = LE.decide("x", tmp_path, STUDY, "S003", SRCS, {}, {"S003": "text"})
    assert d["outcome"] == LE.UNKNOWN_LINE and d["downgraded_from"] == LE.SUPERSEDED


def test_a_held_newer_work_allows_the_line(tmp_path):
    srcs = SRCS + [{"id": "S009", "title": "Hunt X et al. 2025", "newer_edition_of": "S003"}]
    d = LE.decide("x", tmp_path, STUDY, "S003", srcs, {}, {"S003": "old", "S009": "new"})
    assert d["outcome"] == LE.DISCLOSED and d["evidence"] == {"kind": "newer work held", "source": "S009"}
    # the same newer work, not held: the gate alone
    (tmp_path / "n").mkdir()
    d2 = LE.decide("x", tmp_path / "n", STUDY, "S003", srcs, {}, {"S003": "old"})
    assert d2["outcome"] == LE.UNKNOWN_LINE


def _preflight(tmp_path, monkeypatch, decision, amend=None):
    import bindings as B
    import source_store as store
    case = tmp_path / "case"
    (case / "rulings").mkdir(parents=True)
    (case / "draft").mkdir()
    (case / "sources.json").write_text(json.dumps({"sources": SRCS}))
    (case / "draft" / "x.html.gate.json").write_text(json.dumps({"recency": {"studies": [STUDY]}}))
    if amend:
        _errata(case, "S003", [amend])
    rec = dict(decision, key=LE.study_key(STUDY), study=STUDY["name"], old_source="S003")
    (case / "rulings" / "lean_editions.jsonl").write_text(json.dumps(rec) + "\n")
    monkeypatch.setattr(store, "case_dir", lambda slug: case)
    monkeypatch.setattr(store, "held", lambda slug: {"S003": {"sha256": "x"}})
    return LE.preflight_rows("x", [rec["sentence"]])


def test_preflight_stops_a_recorded_line_that_rests_on_the_gate_alone(tmp_path, monkeypatch):
    line = LE.line_for(SRCS, "S003")
    rows = _preflight(tmp_path, monkeypatch, {"outcome": LE.DISCLOSED, "sentence": line})
    assert rows[0][1] == LE.BAD and "rest on the gate's web search alone" in rows[0][2]


def test_preflight_passes_the_line_with_its_registry_record(tmp_path, monkeypatch):
    line = LE.line_for(SRCS, "S003")
    rows = _preflight(tmp_path, monkeypatch, {"outcome": LE.DISCLOSED, "sentence": line},
                      amend={"type": "Update in", "id": "40123456", "source": "MED"})
    assert rows[0][1] == LE.OK, rows


def test_sweep_of_recorded_disclosures():
    """Every recorded DISCLOSED decision in the case folders, checked against the case's own registry records."""
    found, bare = 0, []
    for f in sorted(glob.glob(str(ROOT / "issues" / "*" / "rulings" / "lean_editions.jsonl"))):
        case = Path(f).parent.parent
        try:
            srcs = json.loads((case / "sources.json").read_text()).get("sources") or []
        except OSError:
            continue
        for ln in Path(f).read_text().splitlines():
            d = json.loads(ln)
            if d.get("outcome") != LE.DISCLOSED:
                continue
            found += 1
            # every listed source counted as held: an upper bound on what could support the line
            if LE.newer_evidence(case, d.get("old_source"), srcs, {s.get("id") for s in srcs}) is None:
                bare.append((case.name, d.get("old_source")))
    if not found:
        pytest.skip("no recorded case folders here")
    # recorded 2026-11-27: 9 lines in 7 folders, every one on the gate's web search alone (6 rested on a
    # corrigendum; L1-01b's has no matched old source); each now STOPs the row 'newer editions handled'
    assert found == 9 and len(bare) == 9, bare
