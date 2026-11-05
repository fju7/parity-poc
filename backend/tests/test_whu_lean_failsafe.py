"""Lean WHU: the ruling paths (process doc §4.6.1; advisor's ruling of
2026-11-05 on the Q1-02 lean run). Offline, $0.

    backend/venv/bin/python -m pytest -q backend/tests/test_whu_lean_failsafe.py

(1) "Not material" that the body already states becomes "already stated" and
    stays off the readers' list.
(2) A finding ruling.py would leave for a person on a protected or ambiguous
    sentence removes the sentence instead; it is recorded as "removed:
    unresolved finding", and nothing decides or closes it.
(3) Q1-02's two contradiction lines leave the page; round 1's recorded person
    routings, replayed through the lean router.
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import lean  # noqa: E402
import lean_failsafe as LF  # noqa: E402
import lean_sentences as LS  # noqa: E402
import coverage_check as C  # noqa: E402
import ruling as R  # noqa: E402

Q2 = "whu-lean-q1-02"
Q2_CASE = ROOT / "issues" / "WHU-L1-02-whu-lean-q1-02"
ROUND1 = {"whu-quarterly-r1-01": "WHU-Q1-01-whu-quarterly-r1-01", "whu-quarterly-r1-02": "WHU-Q1-02-whu-quarterly-r1-02",
          "whu-quarterly-r1-03": "WHU-Q1-03-whu-quarterly-r1-03", "whu-quarterly-r1-04": "WHU-Q1-04-whu-quarterly-r1-04"}
LINE1 = "S001@119214-119377"      # the review's cognitive-skills sentence: the body states it
LINE2 = "S001@119378-119555"      # speech and school behaviour: the body does not state it whole


@pytest.fixture
def lean_on():
    lean.enable(True)
    yield
    lean._forced = None


def _person_rows(case: Path) -> list[dict]:
    p = case / "rulings" / "for_person.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def _tree_sha(case: Path) -> str:
    """Every file of the case folder that records a decision or a closure."""
    h = hashlib.sha256()
    for p in sorted(case.rglob("*")):
        if p.is_file() and (p.suffix in (".json", ".md") or p.name.endswith("adjudication.md")):
            h.update(str(p.relative_to(case)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def _replay(rows: list[dict], log: Path) -> list[dict]:
    """Each recorded person routing, sent again through the lean router."""
    left = []
    for r in rows:
        it = {"protected": r["protected"], "sentence": r.get("sentence"), "kind": r.get("kind"),
              "ref": r.get("ref") if isinstance(r.get("ref"), dict) else {"raw": r.get("ref")}}
        left += R.route_to_person(r["mode"], [it], log)
    return left


# ------------------------------------------------------------ unit: the router

def test_off_lean_a_protected_item_still_goes_to_a_person(tmp_path):
    lean.enable(False)
    log = tmp_path / "rulings" / "rulings.jsonl"
    log.parent.mkdir()
    left = R.route_to_person("changecheck", [{"protected": "scope", "sentence": "Outside this question: “x” (A [1]).",
                                              "kind": "changecheck: CONTRADICTION", "ref": {"finding_key": "k"}}], log)
    assert len(left) == 1 and (tmp_path / "rulings" / R.FOR_PERSON).exists()
    assert not LF.path_for(log).exists()
    lean._forced = None


@pytest.mark.parametrize("kind", ["question", "reading", "scope", "ambiguous"])
def test_on_lean_a_protected_item_removes_its_sentence_and_goes_to_no_person(tmp_path, lean_on, kind):
    log = tmp_path / "rulings" / "rulings.jsonl"
    log.parent.mkdir()
    it = {"protected": kind, "sentence": "We hold the full text of the review [1].", "kind": "gate: X",
          "ref": {"finding_key": "abc"}}
    assert R.route_to_person("gate", [it], log) == []
    assert not (tmp_path / "rulings" / R.FOR_PERSON).exists()
    rec = LF.load(log)
    assert len(rec) == 1 and rec[0]["outcome"] == LF.OUTCOME and rec[0]["path"] == "gate"
    assert rec[0]["finding_key"] == "abc" and LF.label(rec[0]) == "removed: unresolved finding (gate, gate: X)"
    R.route_to_person("gate", [it], log)
    assert len(LF.load(log)) == 1                       # idempotent


@pytest.mark.parametrize("why", ["licensed source", "relevance words unverified", "relevance unusable",
                                 "omission: no place for the ADD: the anchor is not on the page"])
def test_on_lean_a_reason_that_is_not_a_protected_sentence_still_goes_to_a_person(tmp_path, lean_on, why):
    log = tmp_path / "rulings" / "rulings.jsonl"
    log.parent.mkdir()
    left = R.route_to_person("omissions", [{"protected": why, "sentence": "S001@1-2", "kind": "x", "ref": {}}], log)
    assert len(left) == 1 and not LF.path_for(log).exists()


def test_the_gate_writes_no_not_ruled_protected_closure_for_what_the_fail_safe_takes():
    import inspect
    src = inspect.getsource(R.rule_gate)
    assert 'person = route_to_person("gate", person, log_path(slug))' in src


def test_a_removed_required_element_stops_the_page(lean_on):
    gen = LS.generate({"question": "Does X work?"}, [{"id": "S001", "title": "A review", "access": {"state": "full_text"}}],
                      {"searched": ["the web"]}, [])
    q = next(g for g in gen if g["kind"] == "question")
    gone = {LS.words(q["sentence"])}
    req = LF.required_removed(gen, gone)
    assert req and req[0]["kind"] == "question"
    live = [g for g in gen if not LF.is_removed(g["sentence"], gone)]
    row = LS.check([g["sentence"] for g in live], live, gone, req)
    assert row[1] == LS.BAD and LF.REQUIRED in row[2]


def test_a_removed_readers_list_line_is_not_required_and_the_heading_leaves_with_the_last_line(lean_on):
    decl = [{"key": "S001@1-9", "source": "S001", "state": "not_material",
             "sentence": "Judged not material to this question: “A finding.” (A review [1])."}]
    gen = LS.generate({"question": "Does X work?"}, [{"id": "S001", "title": "A review", "access": {"state": "full_text"}}],
                      {}, decl)
    gone = {LS.words(decl[0]["sentence"])}
    assert LF.required_removed(gen, gone) == []
    live = [g for g in gen if not LF.is_removed(g["sentence"], gone)]
    assert any(g["field"] == "coverage_check.HEADING" for g in live)      # generate() keeps it; generated() drops it
    page = [g["sentence"] for g in live if g["field"] != "coverage_check.HEADING"]
    live = [g for g in live if g["field"] != "coverage_check.HEADING"]
    assert LS.check(page, live, gone, [])[1] == LS.OK
    still = LS.check(page + [decl[0]["sentence"]], live, gone, [])
    assert still[1] == LS.BAD and "still on the page" in still[2]


# ------------------------------------------------------------ Q1-02's records

@pytest.mark.skipif(not (Q2_CASE / "rulings" / "for_person.jsonl").exists(), reason="Q1-02's lean records absent")
def test_q1_02_both_contradiction_lines_leave_the_page_and_no_finding_is_marked_resolved(tmp_path, lean_on, monkeypatch):
    held = R.held_texts(Q2)
    # (1) the conversion takes LINE1 off the list
    hidden = []
    listed = C.declarations(Q2, held, hidden=hidden)
    conv = {d["key"]: d for d in hidden if d.get("converted_from")}
    assert set(conv) == {LINE1} and conv[LINE1]["converted_from"] == "not_material"
    assert not LS.is_framed(conv[LINE1]["stated_by"])        # stated by a body sentence, not by its own line
    assert [d["key"] for d in listed] == [LINE2]
    line2 = listed[0]["sentence"]
    # (2) changecheck's two routings, replayed through the lean router
    before = _tree_sha(Q2_CASE)
    rows = _person_rows(Q2_CASE)
    assert [r["mode"] for r in rows] == ["changecheck", "changecheck"]
    log = tmp_path / "rulings" / "rulings.jsonl"
    log.parent.mkdir()
    assert _replay(rows, log) == []
    assert not (tmp_path / "rulings" / R.FOR_PERSON).exists()
    rec = LF.load(log)
    assert len(rec) == 2 and all(r["outcome"] == LF.OUTCOME and r["path"] == "changecheck" for r in rec)
    # no finding marked resolved: the replay wrote nothing into the case folder
    assert _tree_sha(Q2_CASE) == before
    dispositions = json.loads((Q2_CASE / "change-reviews.json").read_text()).get("dispositions") or []
    keys = {r["ref"]["raw"] if "raw" in r["ref"] else r["ref"].get("finding_key") for r in rec}
    assert not any(d.get("key") in str(keys) for d in dispositions)
    # (3) with the removals on the record, neither line is generated, and both must be off the page
    monkeypatch.setattr(LF, "removed", lambda slug: rec if slug == Q2 else [])
    gen = LS.generated(Q2)
    assert not any(g["kind"] == "scope" for g in gen)              # no line left, so no heading either
    full = LS.generated(Q2, keep_removed=True)
    gone = LF.removed_words(Q2)
    assert LF.is_removed(line2, gone) and LF.required_removed(full, gone) == []
    import bindings as B
    page = B.page_sentences(Q2)
    on_page = LS.check(page, gen, gone, [])
    assert on_page[1] == LS.BAD                                   # the current page still carries them
    off = [s for s in page if not LF.is_removed(s, gone) and not s.startswith(("Judged not material", C.HEADING))]
    assert LS.check(off, gen, gone, [])[1] == LS.OK


# ------------------------------------------------------------ round 1's four audits

def _round1_rows():
    out = []
    for slug, folder in ROUND1.items():
        for r in _person_rows(ROOT / "issues" / folder):
            out.append((slug, r))
    return out


@pytest.mark.skipif(not (ROOT / "issues" / ROUND1["whu-quarterly-r1-04"]).exists(), reason="round 1's records absent")
def test_round1_every_person_routing_on_a_protected_sentence_is_taken_by_the_fail_safe(tmp_path, lean_on):
    rows = [(s, r) for s, r in _round1_rows() if r["protected"] in LF.REMOVABLE]
    assert len(rows) == 4                    # Q1-02 advocate x2, Q1-04 changecheck x2
    log = tmp_path / "rulings" / "rulings.jsonl"
    log.parent.mkdir()
    assert _replay([r for _s, r in rows], log) == []
    assert {r["path"] for r in LF.load(log)} == {"advocate", "changecheck"}


@pytest.mark.skipif(not (ROOT / "issues" / ROUND1["whu-quarterly-r1-04"]).exists(), reason="round 1's records absent")
def test_round1_what_remains_for_a_person_under_lean_is_named(tmp_path, lean_on):
    """The ruling asks for zero person routings across all paths on round 1's
    four audits. The fail-safe reaches findings on protected sentences only;
    round 1 also has 12 routings that are not on a page sentence (9 relevance
    judgements whose question words code could not verify, 3 omission ADDs with
    no place on the page). They are pinned here, by path and reason, for the
    advisor's ruling: they are NOT made to pass."""
    log = tmp_path / "rulings" / "rulings.jsonl"
    log.parent.mkdir()
    left = _replay([r for _s, r in _round1_rows()], log)
    from collections import Counter
    got = Counter(it["protected"] for it in left)
    assert got == Counter({"relevance words unverified": 9,
                           "omission: no place for the ADD: the anchor is not on the page": 3})


@pytest.mark.xfail(strict=True, reason="awaiting the advisor's ruling: 12 round-1 routings are not on a page "
                                       "sentence, so the fail-safe does not reach them (see the test above)")
@pytest.mark.skipif(not (ROOT / "issues" / ROUND1["whu-quarterly-r1-04"]).exists(), reason="round 1's records absent")
def test_round1_zero_person_routings_across_all_paths(tmp_path, lean_on):
    log = tmp_path / "rulings" / "rulings.jsonl"
    log.parent.mkdir()
    assert _replay([r for _s, r in _round1_rows()], log) == []
