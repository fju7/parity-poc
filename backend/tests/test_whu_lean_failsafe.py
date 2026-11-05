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
#
# Round 1 (full WHU) recorded 16 person routings. Replayed through the lean paths:
# 4 on protected sentences -> the fail-safe; 9 relevance judgements code could
# not verify -> treated as relevant (rule_judgements); 3 ADDs with no place ->
# "Not added" lines (rule_omissions). Zero are left for a person.

R1_RELEVANCE = {"whu-quarterly-r1-03": 4, "whu-quarterly-r1-04": 5}
R1_PRESENT = (ROOT / "issues" / ROUND1["whu-quarterly-r1-04"]).exists()


def _round1_rows():
    out = []
    for slug, folder in ROUND1.items():
        for r in _person_rows(ROOT / "issues" / folder):
            out.append((slug, r))
    return out


class _Relevance:
    """A ruling model that answers 'relevant' with words code cannot verify
    for the candidates in UNVERIFIED, and 'not_relevant' for the rest."""
    model = "fake"

    def __init__(self, texts):
        self.texts = texts

    def __call__(self, prompt, max_tokens, role):
        import re
        hit = any(all(w in prompt for w in re.findall(r"[A-Za-z]{5,}", t)[:15]) for t in self.texts)
        if hit:
            return json.dumps({"relevant": True, "question_words": "zqxv unverifiable words",
                               "reason": "fake"}), {}
        return json.dumps({"relevant": False, "question_words": "", "reason": "fake"}), {}


def _key_at(key: str) -> tuple[str, list[int]]:
    sid, rng = key.split("@")
    a, b = rng.split("-")
    return sid, [int(a), int(b)]


def _lean_replay_all(tmp_path) -> dict:
    """Replay every round-1 person routing through the lean paths. Returns
    {left, failsafe, relevant, no_place, declared}."""
    import judgements as J
    import omissions as O
    import premise as PM
    out = {"left": [], "failsafe": [], "relevant": {}, "no_place": {}, "declared": {}}
    rows = _round1_rows()
    for slug in ROUND1:
        mine = [r for s, r in rows if s == slug]
        case = tmp_path / slug
        (case / "rulings").mkdir(parents=True)
        log = case / "rulings" / "rulings.jsonl"
        held = R.held_texts(slug)
        # protected sentences: the router
        prot = [r for r in mine if r["protected"] in LF.REMOVABLE]
        out["left"] += _replay(prot, log)
        out["failsafe"] += LF.load(log)
        # relevance: rule_judgements itself, on round 1's candidates, with a model whose words fail
        rel = [r for r in mine if r["mode"] == "judgements"]
        if rel:
            texts = [held[_key_at(r["sentence"])[0]][slice(*_key_at(r["sentence"])[1])] for r in rel]
            cands = [c for c in J.candidates(held) if c["key"] in {r["sentence"] for r in rel}]
            assert len(cands) == len(rel)
            R.rule_judgements(slug, _Relevance(texts), held=held, scope=PM.scope_of(slug), case=case)
            doc = J.load(case)["candidates"]
            out["relevant"][slug] = sorted(k for k, e in doc.items() if e.get("by") == LF.LEAN_RELEVANT_BY)
            assert all(doc[k]["relevant"] is True and not doc[k]["to_person"] for k in out["relevant"][slug])
        # omissions with no place: the lean branch rule_omissions takes
        om = [r for r in mine if r["mode"] == "omissions"]
        if om:
            priv = ROOT / "issues" / ROUND1[slug] / "rulings" / "omissions.jsonl"
            recs = [json.loads(l) for l in priv.read_text().splitlines()
                    if json.loads(l).get("outcome") == "TO_PERSON"]
            assert len(recs) == len(om)
            # each routing in time order, with the advocate item(s) it carried (for_person.jsonl's
            # ref.origins) and its finding key (the private TO_PERSON record written at the same second)
            out["routings"] = []
            for r, p in zip(om, recs):
                assert r["at"] == p["at"], (r["at"], p["at"])
                sid, at = _key_at(p["key"])
                f = {"source": sid, "at": at, "origins": r["ref"]["origins"], "held_sha256": J.sha(held[sid]),
                     "quote": held[sid][at[0]:at[1]]}
                R.lean_no_place(case, f, held, "no place for the ADD: the anchor is not on the page")
                out["routings"].append((r["at"], tuple(r["ref"]["origins"]), p["key"]))
            out["no_place"][slug] = [e["key"] for e in O.load(case)["omissions"]
                                     if e["outcome"] == O.NOT_ADDED_NO_PLACE]
            out["no_place_origins"] = {e["key"]: e["origins"] for e in O.load(case)["omissions"]
                                       if e["outcome"] == O.NOT_ADDED_NO_PLACE}
            out["declared"][slug] = C.declarations(slug, held, case=case)
        out["left"] += [r for r in mine if r["mode"] not in ("judgements", "omissions")
                        and r["protected"] not in LF.REMOVABLE]
        assert not (case / "rulings" / R.FOR_PERSON).exists(), slug
    return out


@pytest.mark.skipif(not R1_PRESENT, reason="round 1's records absent")
def test_round1_zero_person_routings_across_all_paths(tmp_path, lean_on):
    got = _lean_replay_all(tmp_path)
    assert got["left"] == []
    assert len(got["failsafe"]) == 4 and {r["path"] for r in got["failsafe"]} == {"advocate", "changecheck"}
    assert {s: len(k) for s, k in got["relevant"].items()} == R1_RELEVANCE
    assert {s: len(k) for s, k in got["no_place"].items()} == {"whu-quarterly-r1-03": 2}   # 3 routings, 2 findings
    assert len(_round1_rows()) == 16


@pytest.mark.skipif(not R1_PRESENT, reason="round 1's records absent")
def test_round1_no_place_adds_become_code_written_not_added_lines(tmp_path, lean_on):
    got = _lean_replay_all(tmp_path)
    lines = [d["sentence"] for d in got["declared"]["whu-quarterly-r1-03"]]
    assert len(lines) == 2
    for ln in lines:
        assert ln.startswith("Not added: “") and ln.endswith("(no place on the page).")
        assert LF.is_no_place_line(ln)
    # TRACEABILITY (advisor, 2026-11-05): 3 routings, 2 lines. Routings 1 and 3 are the same
    # advocate item (S001-02) and the same finding, routed by two ruling runs; routing 2 is S003-20.
    assert got["routings"] == [("2026-10-29T12:06:40+00:00", ("S001-02",), "S001@80000-80230"),
                               ("2026-10-29T12:07:14+00:00", ("S003-20",), "S003@21125-21223"),
                               ("2026-10-29T12:53:24+00:00", ("S001-02",), "S001@80000-80230")]
    by_line = {d["key"]: d["sentence"] for d in got["declared"]["whu-quarterly-r1-03"]}
    assert set(by_line) == {"S001@80000-80230", "S003@21125-21223"}
    assert got["no_place_origins"] == {"S001@80000-80230": ["S001-02"], "S003@21125-21223": ["S003-20"]}
    # every routing's item and finding is carried by exactly one line
    for _at, origins, key in got["routings"]:
        assert key in by_line and set(origins) <= set(got["no_place_origins"][key])
    assert "approaching 2 m by 2100" in by_line["S001@80000-80230"]
    assert "18 [5 to 31] % and 36 [16 to 56] %" in by_line["S003@21125-21223"]


@pytest.mark.skipif(not R1_PRESENT, reason="round 1's records absent")
def test_a_relevance_judgement_treated_as_relevant_must_be_stated_or_declared(tmp_path, lean_on):
    """Round 1's Q1-04 candidate S004@129779-131269, treated as relevant on an
    empty record: the page neither states nor declares it -> the judgements row
    BLOCKs (Not Ready)."""
    import judgements as J
    slug = "whu-quarterly-r1-04"
    held = R.held_texts(slug)
    c = next(c for c in J.candidates(held) if c["key"] == "S004@129779-131269")
    case = tmp_path / "case"
    (case / "rulings").mkdir(parents=True)
    done = []
    R._lean_relevant(case, c, held, "", "relevance refused by code: no words", None, done)
    e = J.load(case)["candidates"][c["key"]]
    assert e["relevant"] is True and e["by"] == LF.LEAN_RELEVANT_BY and not e["to_person"]
    rows = [r for r in J.preflight_rows(slug, held=held, rows={}, case=case)]
    assert rows[0][1] != "ok" and "neither stated with their certainty nor declared" in rows[0][2], rows


def test_a_finding_on_a_not_added_line_stops_the_page_and_does_not_remove_it(tmp_path, lean_on):
    line = "Not added: “A finding the page had no place for.” (A review [1]) (no place on the page)."
    log = tmp_path / "rulings" / "rulings.jsonl"
    log.parent.mkdir()
    assert R.route_to_person("changecheck", [{"protected": "scope", "sentence": line,
                                              "kind": "changecheck: CONTRADICTION",
                                              "ref": {"finding_key": "nf1"}}], log) == []
    rec = LF.load(log)
    assert len(rec) == 1 and rec[0]["outcome"] == LF.STOP
    # not a removal: the line is still generated, and the page stops
    stops = [r for r in rec if r["outcome"] == LF.STOP]
    gone = {LS.words(r["sentence"]) for r in rec if r["outcome"] == LF.OUTCOME}
    assert gone == set()
    decl = [{"key": "S001@1-9", "source": "S001", "state": C.NO_PLACE, "sentence": line}]
    gen = LS.generate({"question": "Does X work?"},
                      [{"id": "S001", "title": "A review", "access": {"state": "full_text"}}], {}, decl)
    assert LF.required_removed(gen, gone) == []
    row = LS.check([g["sentence"] for g in gen], gen, gone, [], stops)
    assert row[1] == LS.BAD and LF.STOP in row[2]
    assert not (tmp_path / "rulings" / R.FOR_PERSON).exists()


def test_the_not_added_no_place_line_is_never_dropped_as_furniture_or_converted(lean_on):
    import coverage_check as CC
    assert CC.declaration_sentence(CC.NO_PLACE, "Table 3.", "A review [1]", None) == \
        "Not added: “Table 3.” (A review [1]) (no place on the page)."


def test_one_finding_routed_to_no_place_under_two_items_gives_one_line_carrying_both(tmp_path, lean_on, monkeypatch):
    """Advisor, 2026-11-05: the same finding sent to "no place" by two different
    advocate items -> one readers'-list line whose record keeps both item
    numbers, and neither item counts as an open objection."""
    import omissions as O
    import source_advocate as SA
    held = {"S001": "Intro text. Sea level will rise by up to 2 m by 2100 under very high emissions. More text."}
    at = [12, 79]
    case = tmp_path / "case"
    (case / "rulings").mkdir(parents=True)
    why = "no place for the ADD: the anchor is not on the page"
    for head in ("S001-03", "S001-07"):
        R.lean_no_place(case, {"source": "S001", "at": at, "origins": [head], "held_sha256": "x",
                               "quote": held["S001"][at[0]:at[1]]}, held, why)
    R.lean_no_place(case, {"source": "S001", "at": at, "origins": ["S001-03"], "held_sha256": "x",
                           "quote": held["S001"][at[0]:at[1]]}, held, why)      # a repeat adds nothing
    ents = [e for e in O.load(case)["omissions"] if e["outcome"] == O.NOT_ADDED_NO_PLACE]
    assert len(ents) == 1 and ents[0]["origins"] == ["S001-03", "S001-07"]
    # one line
    monkeypatch.setattr(C, "_sources", lambda slug: [{"id": "S001", "title": "A review"}])
    monkeypatch.setattr(C, "_body_sentences", lambda slug: [])
    lines = C.declarations("demo", held, case=case)
    assert len(lines) == 1 and LF.is_no_place_line(lines[0]["sentence"])
    # no open objection: both items are listed as "Not added", neither is open
    monkeypatch.setattr(SA.sl, "case_dir", lambda slug: case)
    assert SA.no_place_items("demo") == {"S001-03", "S001-07"}
    chunks = [("a-adjudication.md", h, "### %s\nOMISSION:\nDID:\n" % h, "objections") for h in ("S001-03", "S001-07")]
    monkeypatch.setattr(SA, "_chunks", lambda slug: chunks)
    monkeypatch.setattr(SA, "protected_check", lambda slug: (lambda s: False))
    monkeypatch.setattr(SA, "removed_items", lambda slug: [])
    assert SA.open_items("demo") == ([], [])
    # and without the merge the older item would be open (the gap this closes)
    O.record(case, {"source": "S001", "at": at, "origins": ["S001-07"], "held_sha256": "x"},
             outcome=O.NOT_ADDED_NO_PLACE, reason=why, by=R.NO_PLACE_BY)
    assert SA.open_items("demo")[0] == ["a-adjudication.md: S001-03"]
