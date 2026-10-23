"""A recency study is matched to one source by its authors and title together (2026-10-22).

The gate names a study "Cuijpers, Karyotaki, Ciharova et al. -- Psychological
treatments of depression in children and adolescents: ...", and the page
prints the entry as two lines, the authors and the title, so no single line
named it: WHU-S02's recency finding was attached to nothing, and ruling.py
ruled it on the study's name with no passage. findings.recency_match now takes
each source-list entry (author line and title line together) and each
sources.json record (authors, or the "Surname X et al. --" head of the title,
with the rest of the title) as one unit: the first author's surname must be a
word of the study name, and at least 3 distinctive title words must be shared,
with shared / min(title words, study words) >= 0.6. The single best source is
the match. None, or a tie, is RECENCY_UNMATCHED: not ruled, and the preflight
STOPs on it, naming the study.
"""
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))

import findings as F  # noqa: E402
import ruling as R  # noqa: E402

S02_SLUG = "teen-depression-therapy-format"
S02_STUDY = ("Cuijpers, Karyotaki, Ciharova et al. — Psychological treatments of depression in "
             "children and adolescents: response, reliable change, and deterioration (meta-analysis)")


def _s02_present():
    d = ROOT / "issues" / "WHU-S02-teen-depression-therapy-format"
    return (d / "bindings.json").exists() and (d / "sources.json").exists()


@pytest.mark.skipif(not _s02_present(), reason="WHU-S02's bindings are private (gitignored)")
def test_whu_s02_the_cuijpers_study_matches_s006_and_its_four_body_sentences():
    import bindings as B
    rows = B.load(S02_SLUG)["bindings"]
    m = F.recency_attach(S02_SLUG, S02_STUDY, rows)
    assert m["status"] == "matched" and m["source"] == "S006", m
    assert len(m["rows"]) == 4
    entries = F.source_list_text(S02_SLUG)
    for k in m["rows"]:
        r = rows[k]
        assert r.get("on_page") and F._rests_on(r, {"S006"})
        assert not any(F._fold(r["sentence"]) in e for e in entries)      # never a source-list line
    assert F.recency_targets(S02_SLUG, S02_STUDY, rows) == (["S006"], m["rows"])


# --- a synthetic entry printed as an author line and a title line -------------

ENTRY_SOURCES = [
    ("garcia-lopez m, okafor c, et al.", "home blood pressure telemonitoring after stroke: a "
     "randomised trial of nurse-led titration.", ["S1"]),
    ("okafor c, garcia-lopez m.", "home blood pressure telemonitoring after stroke: a cost "
     "analysis of nurse-led titration.", ["S2"]),
    ("lindqvist a, et al.", "dietary sodium and recurrent stroke: a cohort study.", ["S3"]),
]
SRCS = [{"id": "S1", "title": "García-López M et al. — Home blood pressure telemonitoring "
                              "after stroke (Lancet 2025)"},
        {"id": "S2", "title": "Okafor C, García-López M — cost analysis (2025)"},
        {"id": "S3", "title": "Lindqvist A et al. — Dietary sodium and recurrent stroke"}]
STUDY = "Garcia-Lopez, Okafor et al. — nurse-led home blood pressure telemonitoring after stroke"


def test_author_line_and_title_line_are_matched_together():
    m = F.recency_match(STUDY, SRCS, ENTRY_SOURCES)
    assert m["status"] == "matched" and m["source"] == "S1", m
    # S2's first author (Okafor) is in the study name too and its title is
    # nearly the same; the closer title (7 of 8 words against 7 of 9) wins
    assert "garcia-lopez" in m["why"]


def test_neither_line_alone_is_enough():
    title_only = [("", t, ids) for _a, t, ids in ENTRY_SOURCES]
    assert F.recency_match(STUDY, [], title_only)["status"] == F.RECENCY_UNMATCHED   # no surname
    author_only = [(a, "", ids) for a, _t, ids in ENTRY_SOURCES]
    assert F.recency_match(STUDY, [], author_only)["status"] == F.RECENCY_UNMATCHED  # no title


def test_the_surname_is_required_even_with_the_title_whole():
    study = "Brennan et al. — home blood pressure telemonitoring after stroke: nurse-led titration"
    assert F.recency_match(study, SRCS, ENTRY_SOURCES)["status"] == F.RECENCY_UNMATCHED


def test_two_sources_matching_equally_is_unmatched_not_a_guess():
    twins = [("smith j, et al.", "home telemonitoring after stroke in rural clinics.", ["S1"]),
             ("smith j, et al.", "home telemonitoring after stroke in rural clinics.", ["S2"])]
    m = F.recency_match("Smith et al. — home telemonitoring after stroke in rural clinics", [], twins)
    assert m["status"] == F.RECENCY_UNMATCHED and m["candidates"] == ["S1", "S2"]


def test_first_surname():
    assert F.first_surname("cuijpers p, karyotaki e, ciharova m, et al.") == "cuijpers"
    assert F.first_surname("Merry SN et al.") == "merry"
    assert F.first_surname("García-López M") == "garcia-lopez"
    assert F.first_surname("Keles S, Idsoe T") == "keles"
    assert F.first_surname("") == ""


# --- no match: not ruled, and the preflight STOPs naming the study --------------

PAGE = ("<html><head><title>t</title></head><body><p>Mortality fell from 12% to 9%.</p>"
        '<div class="sources"><div class="src"><span class="tag">S1</span>'
        '<a href="https://example.org/a">Smith J, Jones K. Long-term survival in the FOOBAR trial '
        "of a new drug. Example Journal 2024.</a></div></div></body></html>")
ROWS = {"b1": {"sentence": "Mortality fell from 12% to 9%.", "on_page": True, "source_id": "S1",
               "span": "mortality fell from 12% to 9%"}}
NOWHERE = "Okonkwo et al. — a registry of paediatric asthma admissions"
REPORT = {"sha256": "cd34ab12" + "0" * 56, "recency": {"studies": [
    {"name": NOWHERE, "status": "UNKNOWN", "draft_uses": "?", "latest_known": "?"}]}}


@pytest.fixture
def issue(tmp_path, monkeypatch):
    d = tmp_path / "issues" / "WHU-S98-xq"
    d.mkdir(parents=True)
    (d / "issue.json").write_text(json.dumps({"slug": "xq", "study": True}))
    (d / "sources.json").write_text(json.dumps({"sources": [
        {"id": "S1", "type": "primary", "url": "https://example.org/a",
         "title": "Long-term survival in the FOOBAR trial of a new drug"}]}))
    (d / "bindings.json").write_text(json.dumps({"bindings": ROWS}))
    import source_store
    import bindings
    monkeypatch.setattr(source_store, "case_dir", lambda slug: d)
    monkeypatch.setattr(bindings, "path", lambda slug: d / "bindings.json")
    monkeypatch.setattr(bindings, "_page_html", lambda slug: PAGE)
    monkeypatch.setattr(bindings, "_is_study", lambda slug: True)
    return d


def test_an_unmatched_study_is_recorded_as_such_not_ruled_and_stops_the_preflight(issue):
    F.scan("xq", REPORT)
    rec = F.load("xq")["findings"][0]
    assert rec["attached_to"]["status"] == F.RECENCY_UNMATCHED
    assert rec["attached_to"]["rows"] == [] and rec["attached_to"]["sources"] == []

    calls = []
    R.rule_gate("xq", lambda *a: calls.append(a), P=types.SimpleNamespace(is_study=lambda s: True),
                report=REPORT, rows=ROWS, held={"S1": "x"})
    assert calls == []                                       # nothing ruled on the study's name
    assert F.load("xq")["findings"][0]["decision"] == ""

    rows = F.check("xq", REPORT)
    stop = [r for r in rows if r[0] == "recency findings attached"]
    assert stop and stop[0][1] == F.BAD
    assert NOWHERE in stop[0][2] and F.RECENCY_UNMATCHED in stop[0][2]


def test_a_matched_study_raises_no_stop_row(issue):
    rep = {"sha256": REPORT["sha256"], "recency": {"studies": [
        {"name": "Smith, Jones — long-term survival in the FOOBAR trial", "status": "UNKNOWN"}]}}
    F.scan("xq", rep)
    assert F.load("xq")["findings"][0]["attached_to"] == {
        "study": "Smith, Jones — long-term survival in the FOOBAR trial", "sources": ["S1"], "rows": ["b1"]}
    assert not [r for r in F.check("xq", rep) if r[0] == "recency findings attached"]


# --- a trial named by its acronym, with no author (2026-10-22, later) ----------

TRIAL_ENTRIES = [
    ("hortobagyi gn, et al.", "ribociclib as first-line therapy for hr-positive advanced breast "
     "cancer (monaleesa-2).", ["S1"]),
    ("im sa, et al.", "overall survival with ribociclib plus endocrine therapy in breast cancer "
     "(monaleesa-7).", ["S2"]),
]
TRIAL_SRCS = [{"id": "S1", "title": "Hortobagyi GN et al. — Ribociclib as first-line therapy"},
              {"id": "S2", "title": "Im SA et al. — Overall survival with ribociclib",
               "notes": "the MONALEESA-7 final analysis; see also MONALEESA-2"},
              {"id": "S3", "title": "Example Health news — a CDK4/6 inhibitor explained"}]


def test_acronyms():
    assert F.acronyms("the MONALEESA-2 trial (SPARX, NHS, CDK4/6, A1)") == ["MONALEESA-2", "SPARX", "NHS", "CDK4"]
    assert F.acronyms("Cuijpers et al. — psychological treatments") == []


def test_an_acronym_in_exactly_one_source_matches_it():
    m = F.recency_match("the MONALEESA-7 trial", TRIAL_SRCS, TRIAL_ENTRIES)
    assert m["status"] == "matched" and m["source"] == "S2", m
    assert "MONALEESA-7" in m["why"]


def test_an_acronym_in_two_sources_is_unmatched():
    # S1's entry and S2's notes both carry MONALEESA-2
    m = F.recency_match("the MONALEESA-2 trial", TRIAL_SRCS, TRIAL_ENTRIES)
    assert m["status"] == F.RECENCY_UNMATCHED and m["candidates"] == ["S1", "S2"]


def test_an_acronym_nowhere_is_unmatched():
    m = F.recency_match("the PALOMA-3 trial", TRIAL_SRCS, TRIAL_ENTRIES)
    assert m["status"] == F.RECENCY_UNMATCHED and m["candidates"] == []
    assert "PALOMA-3 in no source" in m["why"]


def test_the_acronym_must_be_a_whole_word():
    m = F.recency_match("the MONALEESA trial", TRIAL_SRCS, TRIAL_ENTRIES)
    assert m["status"] == F.RECENCY_UNMATCHED          # in both, as part of MONALEESA-2/-7


def test_a_named_author_keeps_the_author_rule():
    # Hortobagyi is S1's first author: the acronym rule does not apply, and the
    # title words do not match, so it stays unmatched
    m = F.recency_match("Hortobagyi et al. — MONALEESA-7", TRIAL_SRCS, TRIAL_ENTRIES)
    assert m["status"] == F.RECENCY_UNMATCHED


def test_an_unmatched_acronym_stops_the_preflight(issue):
    rep = {"sha256": REPORT["sha256"], "recency": {"studies": [
        {"name": "the PALOMA-3 trial", "status": "UNKNOWN"}]}}
    F.scan("xq", rep)
    stop = [r for r in F.check("xq", rep) if r[0] == "recency findings attached"]
    assert stop and stop[0][1] == F.BAD and "the PALOMA-3 trial" in stop[0][2]
