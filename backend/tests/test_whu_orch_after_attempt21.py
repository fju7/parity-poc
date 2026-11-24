"""Advisor's rulings after orchestrator trial 1 attempt 21 (2026-11-24), at $0, on attempt 21's committed records.

(C) one holdings record; no stage loads a blocked or unheld source's text; the page may cite held sources only;
(A) lean / orchestrated: the dangling check flags removed acronyms only;
(B) after the dangling ruling, a recorded "reject" of that exact finding counts as ruled; nothing else does."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
import applied_check as AC  # noqa: E402
import audit_stage as A  # noqa: E402
import bindings as B  # noqa: E402
import holdings as HD  # noqa: E402
import lean  # noqa: E402
import orchestrator as O  # noqa: E402
import reachability as RC  # noqa: E402
import ruling as R  # noqa: E402
import source_store as store  # noqa: E402
import spancheck as SC  # noqa: E402

SLUG = "whu-lean-orch-t1-q1-02u"
A21 = ROOT / "issues" / "WHU-OT1-02u-whu-lean-orch-t1-q1-02u"
PAGE = A21 / "draft" / (SLUG + ".html")
THE_3_SENTENCE = "An evidence and gap map found 50 studies on teacher training"
# what attempt 21's library index held: all three sources' bytes (the trial library is not in the repo)
LIBRARY = {sid: {"file": "docs/%s.xml" % sid, "sha256": sid * 8} for sid in ("S001", "S002", "S003")}


@pytest.fixture
def lean_on(monkeypatch):
    monkeypatch.delenv("WHU_ORCH_STEP", raising=False)
    lean.enable(True)
    yield
    lean.enable(False)
    lean._forced = None


@pytest.fixture
def lean_off(monkeypatch):
    monkeypatch.delenv("WHU_ORCH_STEP", raising=False)
    lean._forced = False
    yield
    lean._forced = None


@pytest.fixture
def a21_library(monkeypatch):
    monkeypatch.setattr(store, "library_held", lambda slug: dict(LIBRARY) if slug == SLUG else {})
    # each fake text shares the question's words, so the draft's retrieval would pick passages from all three
    text = ("Programmes to improve education for children with disabilities in low- and middle-income countries "
            "work; inclusive education programmes for children and young people with disabilities. ") * 6
    monkeypatch.setattr(SC, "_text", lambda slug, sid: text + sid if sid in store.held(slug) else None)


# ----------------------------------------------------------------- (C) one holdings record

def test_the_record_holds_s001_and_blocks_s002_and_s003_with_their_reasons(a21_library):
    rec = HD.record(SLUG)
    assert {k: v["holding"] for k, v in rec.items()} == {"S001": HD.HELD, "S002": HD.BLOCKED, "S003": HD.BLOCKED}
    assert rec["S002"]["reason"].startswith("correction_not_held: Erratum in 37133285")
    assert rec["S003"]["reason"].startswith("correction_unread: Erratum in 36913230")
    assert HD.held_ids(SLUG) == {"S001"}


def test_a_source_with_no_stored_bytes_is_not_held(monkeypatch):
    monkeypatch.setattr(store, "library_held", lambda slug: {"S001": LIBRARY["S001"]})
    monkeypatch.setattr(store, "sources", lambda slug: [{"id": "S001", "access": {"state": "full_text_held"}},
                                                        {"id": "S002", "access": {"state": "not_opened"}}])
    assert HD.record(SLUG)["S002"]["holding"] == HD.NOT_HELD


def test_the_gate_every_text_reader_goes_through_drops_the_blocked_sources(a21_library):
    assert store.blocked_ids(SLUG) == {"S002", "S003"}
    assert sorted(store.held(SLUG)) == ["S001"]


def test_the_audit_and_every_ruling_see_s001_only(a21_library):
    """Attempt 21's dangling ruling was shown S003's text (PMC9700054) through ruling.held_texts."""
    assert sorted(A.held_for_audit(SLUG)) == ["S001"]
    assert sorted(R.held_texts(SLUG)) == ["S001"]


def test_the_draft_is_given_no_passage_of_a_blocked_source(a21_library):
    """Attempt 21's draft drew 12 of its 38 passages from S002 and S003."""
    ctx = SimpleNamespace(case=A21, slug=SLUG)
    got = O._passages(ctx)
    assert got and {p["source"] for p in got.values()} == {"S001"}


def test_reachability_drops_the_blocked_sources_too(monkeypatch):
    monkeypatch.setattr(RC, "_held_text_all", lambda slug, cache=True: {SLUG + ":S001": "a", SLUG + ":S003": "b"})
    assert RC.held_text(SLUG) == {SLUG + ":S001": "a"}


def test_issues_with_no_blocked_source_are_unchanged():
    """Measured before the change: no issue outside the trial folders has a blocked source in its library index,
    so held() equals the library's index for every one (abstract_held sources stay held)."""
    for issue in sorted((ROOT / "issues").glob("*/issue.json")):
        if issue.parent.name.startswith(("WHU-OT1-", "WHU-SD-")):
            continue
        slug = json.loads(issue.read_text(encoding="utf-8")).get("slug")
        if not slug or not (issue.parent / "sources.json").exists():
            continue
        assert store.held(slug) == store.library_held(slug), slug


def test_attempt_21s_3_sentence_is_refused(a21_library, lean_on):
    found = HD.page_problems(SLUG, B.page_sentences(SLUG, PAGE.read_text(encoding="utf-8")))
    hits = [f for f in found if f.startswith(THE_3_SENTENCE)]
    assert len(hits) == 1 and "[3] S003 is blocked (correction_unread" in hits[0]
    assert any("[2] S002 is blocked (correction_not_held" in f for f in found)
    # the generated record sentences name a blocked source without drawing on it: exempt
    assert not any(f.startswith("A newer edition exists of ") for f in found)


def test_a_sentence_citing_held_sources_only_passes(a21_library):
    assert HD.page_problems(SLUG, ["One trial found it [1].", "No citation here."], generated=[]) == []
    assert HD.page_problems(SLUG, ["It was found [1, 3]."], generated=[])[0].endswith(
        "[3] S003 is blocked (correction_unread: Erratum in 36913230: the notice's text does not name this "
        "source by title, DOI or PMID)")
    assert "[9] names no source" in HD.page_problems(SLUG, ["It was found [9]."], generated=[])[0]


def test_the_lean_preflight_row_stops_attempt_21s_page(a21_library, lean_on):
    rows = HD.preflight_rows(SLUG, PAGE, "ok", "BLOCKED")
    assert rows[0][0] == HD.ROW and rows[0][1] == "BLOCKED" and THE_3_SENTENCE in rows[0][2]


def test_the_lean_preflight_carries_the_row():
    src = (WHU / "publish.py").read_text(encoding="utf-8")
    assert '_sibling("holdings").preflight_rows(slug, page, OK, BAD)' in src


def test_the_standing_check_reports_with_its_prefix(a21_library, lean_on):
    ctx = SimpleNamespace(case=A21, slug=SLUG)
    got = O.holding_problems(ctx, PAGE.read_text(encoding="utf-8"))
    assert got and all(g.startswith(O.HOLDING_PREFIX) for g in got)
    assert any(THE_3_SENTENCE in g for g in got)


# ----------------------------------------------------------------- (A) removed terms: acronyms only

def test_lean_attempt_21s_asia_pacific_is_not_dangling(lean_on):
    assert AC.dangling(A21, PAGE.read_text(encoding="utf-8")) == []


def test_off_attempt_21s_findings_are_unchanged(lean_off):
    got = [(f["term"], f["log"]) for f in AC.dangling(A21, PAGE.read_text(encoding="utf-8"))]
    assert got == [("Asia", "audit/20261124T025314Z/rulings.jsonl:1"),
                   ("Pacific", "audit/20261124T025314Z/rulings.jsonl:1")]


def _one_cut(monkeypatch, old):
    monkeypatch.setattr(AC, "check", lambda case, html: {"checked": [], "inserted": [],
                                                         "cut": [{"ruled_on": old, "log": "r.jsonl:1"}]})
    monkeypatch.setattr(AC, "page_sentences", lambda html: ["First.", "The EGM map by Saran found gaps."])


def test_lean_a_removed_acronym_is_still_dangling(monkeypatch, lean_on):
    _one_cut(monkeypatch, "The evidence and gap map (EGM) of Saran was searched.")
    assert [f["term"] for f in AC.dangling(Path("x"), "")] == ["EGM"]


def test_off_a_removed_capitalised_name_is_still_dangling(monkeypatch, lean_off):
    _one_cut(monkeypatch, "The evidence and gap map (EGM) of Saran was searched.")
    assert [f["term"] for f in AC.dangling(Path("x"), "")] == ["EGM", "Saran"]


# ----------------------------------------------------------------- (B) a recorded reject covers its exact finding

FINDING = {"term": "Asia", "later_sentence": "S.", "log": "audit/r/rulings.jsonl:1"}


def _rulings(tmp_path, *records):
    (tmp_path / "rulings").mkdir()
    (tmp_path / "rulings" / "rulings.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    return tmp_path


def _ruled(ruling="reject", term="Asia", sentence="S.", after="audit/r/rulings.jsonl:1"):
    return {"id": "abc", "ruling_kind": "dangling", "ruling": ruling, "inputs": {"sentence": sentence},
            "covers": [{"term": term, "after_ruling": after, "row": None}]}


def test_attempt_21s_two_rejected_findings_count_as_ruled_and_are_logged(lean_off):
    found = AC.dangling(A21, PAGE.read_text(encoding="utf-8"))
    left, ruled = O.dangling_unruled(A21, found)
    assert left == [] and [r["term"] for r in ruled] == ["Asia", "Pacific"]
    assert all(r["ruled_by"] == "rulings/rulings.jsonl id 9dc6be279aed3549 (reject)" for r in ruled)


@pytest.mark.parametrize("record", [
    _ruled(ruling="amend"),                                   # an amend that still leaves it dangling
    _ruled(term="Pacific"),                                   # another term
    _ruled(sentence="Another sentence."),                     # another later sentence
    _ruled(after="audit/r/rulings.jsonl:2"),                  # another applied ruling
    dict(_ruled(), ruling_kind="gate"),                       # not a dangling ruling
])
def test_only_a_reject_of_that_exact_finding_covers_it(tmp_path, record):
    left, ruled = O.dangling_unruled(_rulings(tmp_path, record), [FINDING])
    assert left == [FINDING] and ruled == []


def test_no_ruling_at_all_leaves_the_finding(tmp_path):
    left, ruled = O.dangling_unruled(tmp_path, [FINDING])
    assert left == [FINDING] and ruled == []


def test_a_matching_reject_covers_it(tmp_path):
    left, ruled = O.dangling_unruled(_rulings(tmp_path, _ruled()), [FINDING])
    assert left == [] and ruled[0]["after_ruling"] == FINDING["log"]
