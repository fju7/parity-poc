"""Lean WHU: post-test fixes 1-7 and rules 3a/3b (process doc §4.6.1, "What 'we
read' means"; advisor's rulings of 5 November 2026 after Q1-04). Offline, $0.

    backend/venv/bin/python3 -m pytest -q backend/tests/test_whu_lean_post_test_fixes.py
"""
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import audit_stage as A  # noqa: E402
import bindings as B  # noqa: E402
import coverage_check as C  # noqa: E402
import lean  # noqa: E402
import lean_editions as LE  # noqa: E402
import lean_failsafe as LF  # noqa: E402
import lean_reading as LRD  # noqa: E402
import lean_received as LR  # noqa: E402
import lean_sentences as LS  # noqa: E402
import omissions as O  # noqa: E402
import ruling as R  # noqa: E402
import source_ledger as SL  # noqa: E402

LEDGER = ROOT / "backend" / "data" / "spend" / "ledger.jsonl"


@pytest.fixture
def lean_on():
    lean.enable(True)
    yield
    lean._forced = None


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else ""


# ------------------------------------------------------------------ fix 1

def test_fix1_the_audit_dry_run_makes_no_paid_call(monkeypatch):
    def no_call(*a, **k):
        raise AssertionError("a dry run built a model caller or started a run")
    monkeypatch.setattr(A, "Caller", no_call)
    monkeypatch.setattr(A, "run", no_call)
    before = _sha(LEDGER)
    got = A.dry_run("deskilling", limit=3)
    assert got["model_calls"] == 0 and got["status"] == "dry_run" and got["units"] == 3
    assert _sha(LEDGER) == before


# ------------------------------------------------------------------ fix 2

def test_fix2_the_public_reason_is_redacted_against_every_held_source(tmp_path):
    held = {"S001": "Alpha beta gamma delta epsilon zeta eta theta iota kappa.",
            "S002": "The second report says rainfall rises sharply over the northern coast by mid century."}
    f = {"source": "S001", "at": [0, 20], "quote": "Alpha beta gamma delta", "origin": "S001-01"}
    reason = "Another source says rainfall rises sharply over the northern coast by mid century, so it is material."
    e = O.record(tmp_path, f, outcome=O.NOT_MATERIAL, reason=reason, by="t", held_text=held)
    assert "[S002@" in e["reason"]
    assert "rainfall rises sharply over the northern coast" not in e["reason"]
    assert O.leaks_source_text(tmp_path, held) == []


def test_fix2_a_single_text_is_still_redacted_as_before(tmp_path):
    held = "one two three four five six seven eight nine ten"
    f = {"source": "S001", "at": [0, 3]}
    e = O.record(tmp_path, f, outcome=O.NOT_MATERIAL, reason="it says one two three four five six seven",
                 by="t", held_text=held)
    assert "[S001@" in e["reason"]


# ------------------------------------------------------------------ fix 3

SRCS = [{"id": "S001", "title": "A review", "also_called": ["A review"], "access": {"state": "full_text_held"}}]


def test_fix3_a_generated_not_read_sentence_does_not_trip_could_not_be_opened():
    sent = "Of A review [1], we did not read: section 4 of the chapter body."
    walls, _loose = SL._inaccessibility(sent, SRCS)
    assert walls, "the pattern itself still matches; only the exemption makes it pass"
    walls2, _ = SL._inaccessibility(sent, SRCS, {SL._exempt_words(sent)})
    assert walls2 == []


def test_fix3_a_hand_written_claim_is_still_caught():
    hand = "We could not open A review, so its methods are not described here."
    gen = "Of A review [1], we did not read: section 4."
    walls, _ = SL._inaccessibility(hand, SRCS, {SL._exempt_words(gen)})
    assert walls


def test_fix3_generated_reading_is_empty_off_lean():
    lean.enable(False)
    try:
        assert SL.generated_reading("whu-lean-q1-04") == set()
    finally:
        lean._forced = None


# ------------------------------------------------------------------ fix 4

def _doc(not_read=None, sections=None, covers=None):
    acc = {"state": "full_text_held"}
    if not_read is not None:
        acc["not_read"] = not_read
    if sections is not None:
        acc["sections"] = sections
    if covers is not None:
        acc["covers_not_read"] = covers
    return {"sources": [{"id": "S001", "access": acc}]}


def test_fix4_a_removed_not_read_record_stops_the_page():
    hist = [_doc(not_read=["the figures and tables as graphics"], sections=["section A"])]
    gone = LRD.removed_not_read(hist, _doc(sections=["section A"]))
    assert gone == ["S001: the figures and tables as graphics"]
    assert LRD.not_read_row(hist, _doc(sections=["section A"]))[1] == LRD.BAD


def test_fix4_it_may_leave_only_with_a_covering_listed_section():
    hist = [_doc(not_read=["section D.1"], sections=["section A"])]
    ok = _doc(sections=["section A", "section D.1"], covers={"section D.1": "section D.1"})
    assert LRD.removed_not_read(hist, ok) == []
    unlisted = _doc(sections=["section A"], covers={"section D.1": "section D.1"})
    assert LRD.removed_not_read(hist, unlisted) == ["S001: section D.1"]
    kept = _doc(not_read=["section D.1"], sections=["section A"])
    assert LRD.not_read_row(hist, kept)[1] == LRD.OK


# ------------------------------------------------------------------ fix 5

HELD = ("Abstract. Warming increases heavy rainfall. " + "x" * 200 +
        " Results. Sea level rises by 0.5 m by 2100 in the middle scenario. " + "y" * 200)


def _rows():
    a = HELD.index("Warming increases")
    b = HELD.index("Sea level rises")
    return {"r1": {"on_page": True, "sentence": "Warming increases heavy rainfall.", "source_id": "S001",
                   "span": HELD[a:a + 32]},
            "r2": {"on_page": True, "sentence": "Sea level rises by half a metre.", "source_id": "S001",
                   "span": HELD[b:b + 50]}}


def test_fix5_a_sentence_resting_outside_received_text_stops_the_page():
    a = HELD.index("Warming increases")
    u = LR._mask(len(HELD), [(a, a + 40)])
    row = LRD.rests_row(_rows(), {"S001": HELD}, {"S001": u})
    assert row[1] == LRD.BAD and "r2" in row[2] and "r1" not in row[2].split("||")[0].split(":")[0]


def test_fix5_received_everywhere_passes_and_the_source_list_is_exempt():
    u = LR._mask(len(HELD), [(0, len(HELD))])
    assert LRD.rests_row(_rows(), {"S001": HELD}, {"S001": u})[1] == LRD.OK
    a = HELD.index("Warming increases")
    u2 = LR._mask(len(HELD), [(a, a + 40)])
    entries = [("Sea level rises by half a metre. IPCC 2021.", [])]
    assert LRD.rests_row(_rows(), {"S001": HELD}, {"S001": u2}, entries)[1] == LRD.OK


# ------------------------------------------------------------------ fix 6

def test_fix6_the_measurement_counts_one_stage_never_stages_added_together(tmp_path):
    held = "A" * 100 + " " + "B" * 100
    ms = {"audit": LR._mask(len(held), [(0, 60)]), "rulings": LR._mask(len(held), [(60, 100)]),
          "advocate": bytearray(len(held))}
    r = LR.section_report(held, ms, "section A", [0, 100])
    assert not r["full"] and r["shares"]["audit"] == 0.6
    ms["audit"] = LR._mask(len(held), [(0, 100)])
    r = LR.section_report(held, ms, "section A", [0, 100])
    assert r["full"] and r["by"] == ["audit"]
    assert not LR.section_report(held, ms, "no offsets", None)["full"]


def test_fix6_rulings_inputs_are_matched_back_to_the_held_text():
    held = "Intro. " + "The ocean will continue to warm through the twenty-first century under all scenarios. " * 3
    m = LR.text_mask(held, ["Quotation 1: \"The ocean will continue to warm through the twenty-first century\""])
    i = held.index("The ocean")
    assert LR.share(held, m, i, i + 60) == 1.0
    assert LR.share(held, m, 0, 6) == 0.0


def test_fix6_the_logs_feed_the_measurement_and_a_carried_ruling_counts_nothing(tmp_path):
    held = "Abstract. " + "Glaciers will keep losing mass for decades even if warming stops today. " * 2
    (tmp_path / "audit" / "r1").mkdir(parents=True)
    (tmp_path / "audit" / "r1" / "retrieval.jsonl").write_text(json.dumps(
        {"unit": "u1", "source": "S001", "bound": [[10, 40]], "retrieved": [[40, 60, 1.0]]}) + "\n")
    (tmp_path / "rulings").mkdir()
    (tmp_path / "rulings" / "rulings.jsonl").write_text(json.dumps(
        {"inputs": {"judgement": held[10:83]}, "carried_from": "abc"}) + "\n")
    (tmp_path / "rulings" / "advocate_reasks.jsonl").write_text(json.dumps(
        {"source": "S001", "delivered": [[90, 120]]}) + "\n")
    ms = LR.masks(tmp_path, "S001", held)
    assert sum(ms["audit"]) == 50 and sum(ms["rulings"]) == 0 and sum(ms["advocate"]) == 30


def test_fix6_the_reading_statement_is_built_from_the_measurement():
    srcs = [{"id": "S001", "title": "A review",
             "access": {"state": "full_text_held", "sections": ["the abstract", "section 5"]}}]
    measured = {"S001": [{"name": "the abstract", "full": True}, {"name": "section 5", "full": False}]}
    s = [g["sentence"] for g in LS.generate({"question": "Q?"}, srcs, measured=measured)]
    assert "Of A review [1], we read: the abstract." in s
    assert ("We searched the full text of A review [1] and checked the passages relevant to each sentence; "
            "we did not read section 5 in full.") in s
    none = [g["sentence"] for g in LS.generate({"question": "Q?"}, srcs, measured={})]
    assert not any(", we read: " in x for x in none)
    assert any(x.endswith("we did not read the abstract, section 5 in full.") or
               "we did not read the abstract; section 5 in full." in x for x in none)
    bare = [{"id": "S001", "title": "A review", "access": {"state": "full_text_held"}}]
    assert any(x.endswith("we did not read it in full.") for x in
               [g["sentence"] for g in LS.generate({"question": "Q?"}, bare, measured={})])


def test_fix6_the_preflight_stops_when_statement_and_measurement_disagree():
    srcs = [{"id": "S001", "title": "A review",
             "access": {"state": "full_text_held", "sections": ["the abstract"]}}]
    gen = LS.generate({"question": "Q?"}, srcs, measured={"S001": [{"name": "the abstract", "full": False}]})
    claim = "Of A review [1], we read: the abstract."
    assert LRD.statement_row([claim], gen)[1] == LRD.BAD
    right = [g["sentence"] for g in gen if g["kind"] == "reading"]
    assert LRD.statement_row(right, gen)[1] == LRD.OK
    # the new frame is a protected reading sentence, and framed
    assert B.protected_kind(right[-1]) == "reading" and LS.is_framed(right[-1])


# ------------------------------------------------------------------ fix 7

class FakeCall:
    model = "claude-sonnet-5-5"

    def __init__(self):
        self.n = 0

    def __call__(self, prompt, max_tokens, role):
        self.n += 1
        return json.dumps({"relevant": True, "question_words": "sea level", "reason": "r"}), {"usd": 0.02}


def test_fix7_the_same_request_under_a_new_id_is_not_paid_for_twice(tmp_path):
    log = tmp_path / "rulings" / "rulings.jsonl"
    p = R.relevance_payload("How will sea level change?", {"covers": "sea level"}, "Sea level will rise.")
    call = FakeCall()
    g1 = R.rule("relevance", p, 0, call, log, {"finding_id": "f1-rec-1"})
    g2 = R.rule("relevance", p, 0, call, log, {"finding_id": "f2-rec-1"})
    assert call.n == 1 and g1 == g2
    recs = [json.loads(l) for l in log.read_text().splitlines()]
    assert recs[1]["carried_from"] == recs[0]["id"] and recs[1]["usage"] == {}
    assert recs[1]["finding_id"] == "f2-rec-1"
    other = R.relevance_payload("How will sea level change?", {"covers": "sea level"}, "Ice sheets shrink.")
    R.rule("relevance", other, 0, call, log, {"finding_id": "f3"})
    assert call.n == 2


def test_fix7_a_record_without_its_answer_is_never_reused(tmp_path):
    log = tmp_path / "rulings.jsonl"
    p = R.relevance_payload("Q?", {}, "A judgement.")
    base = {"ruling_kind": "relevance", "prompt_sha256": R.prompt_sha("relevance"), "model": "claude-sonnet-5-5",
            "inputs_sha256": R.sha(json.dumps(p))}
    log.write_text(json.dumps(dict(base, id="old", relevant=True)) + "\n")
    call = FakeCall()
    R.rule("relevance", p, 0, call, log, {})
    assert call.n == 1


# ------------------------------------------------------------------ rule 3a

def test_rule3a_an_add_beyond_its_finding_becomes_a_required_not_added_line(tmp_path, lean_on):
    held = {"S001": "First sentence of the finding. A second sentence the ruling also quoted."}
    f = {"source": "S001", "at": [0, 30], "quote": held["S001"][:30], "origins": ["S001-03"]}
    got = R.lean_no_place(tmp_path, f, held, R.BEYOND_WHY, O.NOT_ADDED_BEYOND)
    assert got["outcome"] == O.NOT_ADDED_BEYOND
    e = O.load(tmp_path)["omissions"][0]
    assert e["outcome"] == O.NOT_ADDED_BEYOND and e["by"] == R.BEYOND_BY
    line = C.declaration_sentence(C.BEYOND, "First sentence of the finding.", "A review [1]", None)
    assert line == ("Not added: “First sentence of the finding.” (A review [1]) "
                    "(the proposed sentence went beyond the finding).")
    assert LF.is_no_place_line(line)              # required: the fail-safe may not remove it
    assert B.protected_kind(line) == "scope"


# ------------------------------------------------------------------ rule 3b (corrected after Q1-01b)

NEW = "State of CDR, 3rd edition. Total removal is about 2.2 GtCO2 a year. Novel removal is small."
OLD = "State of CDR, 2nd edition. Total removal is about 2 GtCO2 a year. Novel removal is small."
STUDY = {"name": "State of CDR 2nd ed.", "status": "SUPERSEDED",
         "latest_known": "3rd Edition. Published June 2026; 5.5 GtCO2 by 2050."}


def _srcs(with_new: bool):
    s = [{"id": "S002", "title": "The State of Carbon Dioxide Removal, 2nd edition", "edition": "2nd edition (2024)",
          "url": "https://www.stateofcdr.org/2nd", "doi": "10.17605/OSF.IO/E5M86"}]
    if with_new:
        s.append({"id": "S004", "title": "The State of Carbon Dioxide Removal, 3rd edition",
                  "newer_edition_of": "S002"})
    return s


def test_rule3b_the_newer_edition_is_used_when_held_and_every_span_reverifies(tmp_path, monkeypatch):
    import source_store as store
    monkeypatch.setattr(store, "held", lambda slug: {"S004": {"sha256": "new"}})
    rows = {"r1": {"on_page": True, "source_id": "S002", "span": "Novel removal is small.", "document_sha": "old"}}
    saved = []
    d = LE.decide("x", tmp_path, STUDY, "S002", _srcs(True), rows, {"S002": OLD, "S004": NEW}, saved.append,
                  matched_by="identifier (doi)")
    assert d["outcome"] == LE.USED and rows["r1"]["source_id"] == "S004" and rows["r1"]["rebound_from"] == "S002"
    f = {"id": "f1-rec-1"}
    LE.settle_finding(f, d)
    assert f["decision"] == "accepted" and f["source_id"] == "S004" and f["quote"] == "Novel removal is small."


def test_rule3b_the_disclosure_line_is_code_known_text_only(tmp_path):
    rows = {"r1": {"on_page": True, "source_id": "S002", "span": "Total removal is about 2 GtCO2 a year."}}
    d = LE.decide("x", tmp_path, STUDY, "S002", _srcs(True), rows, {"S002": OLD, "S004": NEW})
    assert d["outcome"] == LE.DISCLOSED
    assert d["sentence"] == ("A newer edition exists of The State of Carbon Dioxide Removal, 2nd edition; "
                             "this page uses 2nd edition (2024).")
    assert "5.5" not in d["sentence"] and "June" not in d["sentence"]       # gate prose stays in the records
    assert d["latest_known"] == STUDY["latest_known"]
    assert len(SL.sentences(d["sentence"])) == 1
    # a title the splitter would cut falls back to the numbered label
    dotted = [{"id": "S002", "title": "Smith J. et al. A review. Lancet 2024."}]
    t = LE.line_for(dotted, "S002")
    assert len(SL.sentences(t)) == 1 and "[1]" in t


def test_rule3b_unknown_studies_are_matched_by_every_identifier_and_reported():
    srcs = _srcs(False)
    for study, how in [({"name": "x", "url": "https://www.stateofcdr.org/2nd/"}, "identifier"),
                       ({"name": "see doi 10.17605/osf.io/e5m86 for it"}, "identifier"),
                       ({"name": "The State of Carbon Dioxide Removal report"}, "title overlap")]:
        sid, by = LE.match("x", dict(study, status="UNKNOWN"), srcs, {})
        assert sid == "S002" and by.startswith(how), (study, by)
    sid, by = LE.match("x", {"name": "Unnamed antenatal care studies", "status": "UNKNOWN"}, srcs, {})
    assert sid is None and "no DOI" in by


def test_rule3b_unknown_matched_gets_its_line_and_untied_are_counted_never_dismissed(tmp_path):
    srcs = _srcs(False)
    u = LE.decide("x", tmp_path, {"name": "A", "status": "UNKNOWN", "latest_known": "?"}, "S002", srcs, {}, {},
                  matched_by="identifier (doi)")
    # wording after Q1-04c (advisor, option (b)); the record lists no registry, so "searched" is empty
    assert u["sentence"] == ("Our recency check could not establish whether The State of Carbon Dioxide Removal, "
                             "2nd edition has a newer edition.")
    assert u["searched"] == []
    for n in ("B", "C"):
        LE.decide("x", tmp_path, {"name": n, "status": "UNKNOWN", "latest_known": "?"}, None, srcs, {}, {},
                  matched_by="no DOI, PMID, PMCID, URL, author or title matches a page source")
    ls = [x["sentence"] for x in LE.lines(tmp_path)]
    assert ls == [u["sentence"],
                  "2 recency questions not tied to any source on this page were recorded and not acted on."]
    assert LE.count_line(1) == "1 recency question not tied to any source on this page was recorded and not acted on."
    f = {"id": "f-rec-2"}
    LE.settle_finding(f, LE.decisions(tmp_path)[1])
    assert f["decision"] == "judgement" and "not tied" in f["why"]
    for line in ls:
        assert B.protected_kind(line) == "reading" and LS.is_framed(line) and LE.is_code_line(line)
    gen = LS.generate({"question": "Q?"}, [], editions=LE.lines(tmp_path))
    assert len(LF.required_removed(gen, {LS.words(x) for x in ls})) == 2      # required: never removable


# ------------------------------------------------------- the actual preflight rows, on Q1-01b's records

Q1B = ROOT / "issues" / "WHU-L1-01b-whu-lean-q1-01b"
needs_q1b = pytest.mark.skipif(not (Q1B / "advocate").exists() or not (Q1B / "rulings").exists(),
                               reason="Q1-01b's git-ignored records are only on the operator's machine")


@pytest.fixture
def q1b(tmp_path, monkeypatch):
    import shutil
    import source_store as store
    case = tmp_path / Q1B.name
    shutil.copytree(Q1B, case)
    monkeypatch.setattr(store, "case_dir", lambda slug: case)
    monkeypatch.setattr(SL, "case_dir", lambda slug: case)
    return case


@needs_q1b
def test_q1b_the_two_rows_exclude_the_code_not_added_item_by_id(q1b, lean_on):
    import source_advocate as SA
    om = O.preflight_rows("whu-lean-q1-01b", [], held=R.held_texts("whu-lean-q1-01b"))
    assert om[0][0] == O.ROW and om[0][1] == "ok", om
    rows = {r[0]: r for r in SA.preflight_rows("whu-lean-q1-01b")}
    assert rows["advocate objections closed"][1] == "ok", rows["advocate objections closed"]
    info = [r for r in rows.values() if "Not added" in (r[2] or "") and "S001-03" in r[2]]
    assert info, "the INFO row still reports the item, not closed"


@needs_q1b
def test_q1b_off_lean_the_item_is_still_open(q1b):
    lean.enable(False)
    try:
        om = O.preflight_rows("whu-lean-q1-01b", [], held=R.held_texts("whu-lean-q1-01b"))
        assert om[0][1] == "BLOCKED"
    finally:
        lean._forced = None


@needs_q1b
def test_q1b_recency_findings_settle_by_code_with_code_known_lines(q1b, lean_on):
    import findings as F
    (q1b / "rulings" / "lean_editions.jsonl").unlink(missing_ok=True)
    report = json.loads((q1b / "draft" / "whu-lean-q1-01b.html.gate.json").read_text())
    doc = json.loads((q1b / "gate-findings.json").read_text())
    for f in doc.get("findings") or []:
        if f.get("kind") == "recency":
            f["decision"] = ""
    done = []
    ids = R.lean_editions_gate("whu-lean-q1-01b", report, doc, {}, R.held_texts("whu-lean-q1-01b"), done,
                               write_rows=lambda r: None)
    assert len(ids) == 4                                  # 1 SUPERSEDED + 3 UNKNOWN; the CURRENT one untouched
    ds = LE.decisions(q1b)
    assert all(d.get("matched_by") for d in ds)
    sinema = [d for d in ds if "SINEMA" in (d["study"] or "")][0]
    assert sinema["outcome"] == LE.UNTIED                 # not a source on this page
    for ln in LE.lines(q1b):
        s = ln["sentence"]
        assert "5.5" not in s and "JAMA" not in s and len(SL.sentences(s)) == 1
    page = B.page_sentences("whu-lean-q1-01b")
    assert LE.preflight_rows("whu-lean-q1-01b", page)[0][1] == LE.BAD          # lines not pasted yet
    ok = LE.preflight_rows("whu-lean-q1-01b", page + [x["sentence"] for x in LE.lines(q1b)])
    assert ok[0][1] == LE.OK and "Matched by" in ok[0][2]


@needs_q1b
def test_q1b_figures_row_skips_the_code_lines_and_still_catches_a_stray_figure(q1b, lean_on, monkeypatch):
    import b13
    LE._append(q1b, {"key": "k1", "outcome": LE.UNTIED, "sentence": None})
    LE._append(q1b, {"key": "k2", "outcome": LE.UNTIED, "sentence": None})
    line = LE.lines(q1b)[-1]["sentence"]
    monkeypatch.setattr(b13.B, "page_sentences", lambda slug: [line])
    assert b13.figures_on_page("whu-lean-q1-01b") == []
    monkeypatch.setattr(b13.B, "page_sentences", lambda slug: [line, "The follow-up ran for 5.5 years."])
    row = b13.preflight_rows("whu-lean-q1-01b")[0]
    assert row[0] == "figures in held documents" and row[1] == b13.BAD and "5.5" in row[2]


# ------------------------------------------------------------------ every paid stage capped by default

def test_a_run_cap_in_issue_json_caps_every_paid_call_whatever_the_cap_flag(tmp_path, monkeypatch):
    import stage_cap
    S = stage_cap.S
    (tmp_path / "WHU-L1-09c-x").mkdir()
    (tmp_path / "WHU-L1-09c-x" / "issue.json").write_text(json.dumps(
        {"slug": "whu-test-capped", "study": True, "run_cap_usd": 10}))
    monkeypatch.setattr(S, "ISSUES_DIR", tmp_path)
    spend = [{"at": "2026-11-05T21:00:00+00:00", "issue": "whu-test-capped", "usd": 9.9}]
    monkeypatch.setattr(S, "entries", lambda: spend)
    monkeypatch.setattr(S, "check_day_cap", lambda about_to_spend=0.0: None)
    assert S.cap_for("whu-test-capped") == 10.0
    with pytest.raises(S.OverIssueCap):
        S.check_cap("whu-test-capped", 0.5)       # what every paid call checks, per call
    assert stage_cap.default_cap("whu-test-capped") == pytest.approx(0.1)


def test_paid_stages_default_their_cap_to_what_is_left_never_uncapped(monkeypatch):
    import stage_cap
    import consistency as CS
    monkeypatch.setattr(stage_cap, "default_cap", lambda issue: 1.25)
    seen = {}

    class Stop(Exception):
        pass

    def caller(*a, **k):
        seen["cap"] = k.get("cap")
        raise Stop()
    monkeypatch.setattr(A, "Caller", caller)
    monkeypatch.setattr(R, "require_study", lambda slug, P=None: None)
    monkeypatch.setattr(stage_cap, "guard", lambda *a, **k: None)
    monkeypatch.setattr(R, "pending", lambda cmd, slug: 1)
    with pytest.raises(Stop):
        R.main(["advocate", "whu-lean-q1-01b"])              # no --cap given
    assert seen["cap"] == 1.25
    seen.clear()
    monkeypatch.setattr(A, "run", lambda *a, **k: (_ for _ in ()).throw(Stop()))
    monkeypatch.setattr(A, "_stage_guard", lambda *a, **k: None)
    monkeypatch.setattr(A, "units", lambda slug: [])
    captured = {}
    monkeypatch.setattr(A, "run", lambda slug, **k: (captured.update(k), (_ for _ in ()).throw(Stop()))[1])
    with pytest.raises(Stop):
        A.main(["run", "whu-lean-q1-01b"])
    assert captured["cap"] == 1.25


def test_the_consistency_sample_defaults_its_cap_too(monkeypatch):
    import consistency as CS
    import stage_cap
    monkeypatch.setattr(stage_cap, "default_cap", lambda issue: 0.75)
    seen = {}
    monkeypatch.setattr(CS, "cmd_audit", lambda a: seen.setdefault("cap", a.cap) and 0)
    CS.main(["audit", "whu-lean-q1-01b", "20261105T000000Z"])
    assert seen["cap"] == 0.75                    # min($5, what is left), never uncapped
    monkeypatch.setattr(stage_cap, "default_cap", lambda issue: 9.0)
    seen.clear()
    CS.main(["audit", "whu-lean-q1-01b", "20261105T000000Z"])
    assert seen["cap"] == 5.0


# --- The leak guard matches whole words (advisor's ruling of 6 November 2026,
# after Q1-02b; process doc §4.6.1, "Correction after Q1-02b"). Every test runs
# the actual preflight row, omissions.preflight_rows.

Q2B = ROOT / "issues" / "WHU-L1-02b-whu-lean-q1-02b"
needs_q2b = pytest.mark.skipif(not (Q2B / "omissions.json").exists() or not (Q2B / "rulings").exists(),
                               reason="Q1-02b's records are not on this machine")


@pytest.fixture
def q2b(tmp_path, monkeypatch):
    import shutil
    import source_store as store
    case = tmp_path / Q2B.name
    shutil.copytree(Q2B, case)
    monkeypatch.setattr(store, "case_dir", lambda slug: case)
    monkeypatch.setattr(SL, "case_dir", lambda slug: case)
    return case


@needs_q2b
def test_leak_guard_q1_02b_record_no_longer_flags(q2b, lean_on):
    held = R.held_texts("whu-lean-q1-02b")
    assert held, "Q1-02b's held texts are in the library"
    # the substring "low and middle income countries an" sits in the folded record ...
    assert "low and middle income countries an" in O._fold((q2b / "omissions.json").read_text())
    # ... but no six whole held-text words do, so the row is ok
    row = O.preflight_rows("whu-lean-q1-02b", [], held=held)[0]
    assert row[0] == O.ROW and row[1] == "ok", row
    assert O.leaks_source_text(q2b, held) == []


HELD_LEAK = {"S009": "Background. Inclusive schooling raised attendance among low-income pupils "
                     "in three districts, the authors reported, with no change in test scores."}


def _leak_case(tmp_path, reason):
    case = tmp_path / "case"
    case.mkdir()
    (case / "omissions.json").write_text(json.dumps(
        {"omissions": [{"key": "S009@0-10", "outcome": "NOT_MATERIAL", "reason": reason}]},
        indent=1, ensure_ascii=False), encoding="utf-8")
    return case


def _row(case):
    return O.preflight_rows("whu-lean-q1-leak", [], case=case, held=HELD_LEAK)[0]


@pytest.mark.parametrize("reason", [
    "It says inclusive schooling raised attendance among low-income pupils.",          # verbatim
    "It says INCLUSIVE Schooling Raised attendance among Low-Income pupils.",           # case
    "It says “inclusive schooling, raised attendance; among low—income pupils”.",       # punctuation
    "It says inclusive schooling raised attendance among low income pupils.",           # hyphen dropped
    "It says inclusive schooling raised\nattendance among\r\n low-income pupils.",      # line breaks
])
def test_leak_guard_flags_a_genuine_six_word_run(tmp_path, lean_on, reason):
    row = _row(_leak_case(tmp_path, reason))
    assert row[1] == "BLOCKED" and "S009" in row[2], row


def test_leak_guard_does_not_flag_a_five_word_run(tmp_path, lean_on):
    # "raised attendance among low-income" = five words (low-income folds to two);
    # "schooling" before and "children" after break the run
    row = _row(_leak_case(tmp_path, "Attendance: raised attendance among low-income children, it says."))
    assert row[1] == "ok", row


def test_leak_guard_does_not_match_inside_a_word(tmp_path, lean_on):
    # Q1-02b's shape: the held text's only six-word run ends in "an", and the
    # record has those words ending in "and"; the old substring test flagged it
    held = {"S009": "three districts the authors reported an"}
    case = _leak_case(tmp_path, "in three districts the authors reported and so on")
    assert "three districts the authors reported an" in O._fold((case / "omissions.json").read_text())
    assert O.leaks_source_text(case, held) == []
    assert O.preflight_rows("whu-lean-q1-leak", [], case=case, held=held)[0][1] == "ok"


# ------------------------------------------------------------------ over the additions budget (after Q1-04b)
# Process doc §4.6.1, "Correction after Q1-04b" (advisor's ruling of 6 November 2026).
# Q1-04b's own records, replayed at $0: rule_omissions reuses each recorded ruling
# (fix 7, carried_ruling), so a paid call here is a failure, not a cost.

Q4B = ROOT / "issues" / "WHU-L1-04b-whu-lean-q1-04b"
Q4B_SLUG = "whu-lean-q1-04b"
OVER = ["S002-08", "S002-10", "S002-13", "S002-14"]
needs_q4b = pytest.mark.skipif(not (Q4B / "omissions.json").exists() or not (Q4B / "rulings").exists(),
                               reason="Q1-04b's records are not on this machine")


@pytest.fixture
def q4b(tmp_path, monkeypatch):
    import shutil
    import source_store as store
    case = tmp_path / Q4B.name
    shutil.copytree(Q4B, case)
    monkeypatch.setattr(store, "case_dir", lambda slug: case)
    monkeypatch.setattr(SL, "case_dir", lambda slug: case)
    return case


def _replay_q4b(case: Path):
    """rule_omissions on the copy, with no paid call and S002-08's recorded re-ask."""
    held = R.held_texts(Q4B_SLUG)
    e08 = next(e for e in O.load(case)["omissions"] if e.get("origins") == ["S002-08"])
    asked = []

    def no_call(*a, **k):
        raise AssertionError("a paid ruling call: the replay did not carry the recorded ruling")

    def reask(system, user):
        # S002-08 was re-asked on 6 Nov; omissions.json kept where its new quotation is
        asked.append(json.loads(user)["objection"]["claim_quoted"])
        return {"source_says": held[e08["source"]][e08["at"][0]:e08["at"][1]]}

    before = _sha(LEDGER)
    done = R.rule_omissions(Q4B_SLUG, no_call, held=held, case=case, reask=reask)
    assert _sha(LEDGER) == before
    return held, done, asked


@needs_q4b
def test_over_budget_q1_04b_records_replayed_become_four_not_added_lines(q4b, lean_on):
    # as recorded at the stop: 8 ADDs fill the budget, 4 went to a person
    recorded = {tuple(e["origins"]): e["outcome"] for e in O.load(q4b)["omissions"]}
    assert sorted(o[0] for o, out in recorded.items() if out == O.TO_PERSON) == OVER
    assert sum(1 for out in recorded.values() if out == O.ADD) == 8
    persons = (q4b / "rulings" / "for_person.jsonl").read_text()

    held, done, asked = _replay_q4b(q4b)

    assert sorted(h for d in done for h in d["origins"]) == OVER
    assert {d["outcome"] for d in done} == {O.NOT_ADDED_OVER_BUDGET}
    assert len(asked) <= 1
    # no person routing: nothing new for a person, and no TO_PERSON left
    assert (q4b / "rulings" / "for_person.jsonl").read_text() == persons
    doc = O.load(q4b)["omissions"]
    assert not [e for e in doc if e["outcome"] == O.TO_PERSON]
    over = [e for e in doc if e["outcome"] == O.NOT_ADDED_OVER_BUDGET]
    assert sorted(e["origins"][0] for e in over) == OVER
    assert {e["by"] for e in over} == {R.OVER_BUDGET_BY}
    assert sum(1 for e in doc if e["outcome"] == O.ADD) == 8          # the budget itself is unchanged
    # the advocate items are not closed, and not open either: the row is ok
    row = O.preflight_rows(Q4B_SLUG, [], held=held)[0]
    assert row[0] == O.ROW and row[1] == "ok", row
    # four code-written lines on the readers' list, each a required page element
    lines = [d["sentence"] for d in C.declarations(Q4B_SLUG, held, case=q4b)
             if d["state"] == C.OVER_BUDGET]
    assert len(lines) == 4
    for line in lines:
        assert line.startswith("Not added: “") and line.endswith(" (over the additions budget).")
        assert LF.is_no_place_line(line)            # the fail-safe may not remove it
        assert B.protected_kind(line) == "scope"
        assert len(SL.sentences(line)) == 1
    # code's lines do not count against the declarations budget
    assert C.OVER_BUDGET not in C.COUNTED


@needs_q4b
def test_over_budget_replay_is_idempotent_and_never_rules_the_items_again(q4b, lean_on):
    _replay_q4b(q4b)
    held = R.held_texts(Q4B_SLUG)
    again = R.rule_omissions(Q4B_SLUG, lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")),
                             held=held, case=q4b, reask=lambda s, u: (_ for _ in ()).throw(AssertionError("re-ask")))
    assert again == []


@needs_q4b
def test_over_budget_without_lean_still_goes_to_a_person(q4b):
    lean.enable(False)
    try:
        n = len((q4b / "rulings" / "for_person.jsonl").read_text().splitlines())
        held, done, _ = _replay_q4b(q4b)
        assert {d["outcome"] for d in done} == {O.TO_PERSON}
        assert len((q4b / "rulings" / "for_person.jsonl").read_text().splitlines()) == n + 4
    finally:
        lean._forced = None


def test_over_budget_line_is_code_known_text_only():
    line = C.declaration_sentence(C.OVER_BUDGET, "Removal costs vary widely by method.", "A report [2]", "ignored")
    assert line == "Not added: “Removal costs vary widely by method.” (A report [2]) (over the additions budget)."
    assert LF.is_no_place_line(line)


# ------------------------------------------------------------------ readers'-list lines (after Q1-04c, ruling D)
# Process doc §4.6.1, "Correction after Q1-04c". Q1-03b's post-D records: its "Judged not
# material" line d1624d4c9d8280b0 is unbound, and the old fail-safe recorded it removed.

Q3B = ROOT / "issues" / "WHU-L1-03b-whu-lean-q1-03b"
Q3B_SLUG = "whu-lean-q1-03b"
Q3B_LINE = "d1624d4c9d8280b0"
# Q1-03b's case folder was restored to its pre-D state and step 9 re-run after these tests were written
# (advisor's ruling after Q1-04c; de7fc35), so the post-D records live only in session LT's private copy.
Q3B_POST_D = Path.home() / "Projects" / "whu-study-private" / "lean" / "session_lt" / "d_q103b_postD"
needs_q3b = pytest.mark.skipif(not ((Q3B / "bindings.json").exists() and (Q3B_POST_D / "bindings.json").exists()),
                               reason="Q1-03b's records, or LT's post-D copy, are not on this machine")


@pytest.fixture
def q3b(tmp_path, monkeypatch):
    import shutil
    import source_store as store
    case = tmp_path / Q3B.name
    shutil.copytree(Q3B, case)
    for p in Q3B_POST_D.rglob("*"):                 # overlay the post-D records the tests were written on
        if p.is_file():
            dst = case / p.relative_to(Q3B_POST_D)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
    monkeypatch.setattr(store, "case_dir", lambda slug: case)
    monkeypatch.setattr(SL, "case_dir", lambda slug: case)
    return case


def _decl_rows(rows):
    return {k: r for k, r in rows.items() if r.get("on_page") and LF.is_required_line(r.get("sentence") or "")}


@needs_q3b
def test_declaration_lines_are_bound_by_code_to_the_span_they_quote(q3b, lean_on):
    import changecheck as CC
    held = R.held_texts(Q3B_SLUG)
    rows = B.load(Q3B_SLUG)["bindings"]
    assert not rows[Q3B_LINE].get("span")                       # post-D: the line is unbound
    line = rows[Q3B_LINE]["sentence"]
    assert [f["kind"] for f in CC.deterministic(Q3B_SLUG, [line])] == ["NEW_AND_UNBOUND"]
    import judgements as J
    before_j = J.preflight_rows(Q3B_SLUG, [])
    before_cov = C.preflight_rows(Q3B_SLUG, [])

    doc, unbound, _stale = B.scan(Q3B_SLUG)
    rows = doc["bindings"]
    decl = _decl_rows(rows)
    assert Q3B_LINE in decl and len(decl) >= 2                  # every readers'-list line, not only this one
    for k, r in decl.items():
        assert B.is_declaration_row(r) and r["by"] == B.DECLARATION_BY and k not in unbound
        a, b = r["offsets"]
        assert held[r["source_id"]][a:b] == r["span"]           # verbatim, with its offsets
        assert r["declaration_key"].startswith(r["source_id"] + "@")
    assert CC.deterministic(Q3B_SLUG, [line]) == []             # changecheck cannot find it unbound
    # the binding says what the list shows, not that the page uses the finding
    assert C.preflight_rows(Q3B_SLUG, []) == before_cov       # coverage: a declared unit stays declared
    assert J.preflight_rows(Q3B_SLUG, []) == before_j         # judgements: a declared one is not "stated"
    # the old fail-safe's removal of this required line now reads as a stop: the line
    # stays on the readers' list, and these post-D records are Not Ready (why Q1-03b's
    # own records are restored from the pre-D copy before step 9 is run again)
    assert any(r["fingerprint"] == Q3B_LINE for r in LF.stops(Q3B_SLUG))
    assert LS.words(line) not in LF.removed_words(Q3B_SLUG)
    assert any(d["sentence"] == line for d in C.declarations(Q3B_SLUG, held))


@needs_q3b
def test_a_finding_on_a_declaration_line_stops_the_page_and_never_removes_it(q3b, lean_on):
    line = B.load(Q3B_SLUG)["bindings"][Q3B_LINE]["sentence"]
    assert LF.is_required_line(line)
    got = LF.record("changecheck", {"sentence": line, "kind": "changecheck: FIGURE_IN_NOTHING_HELD",
                                    "protected": "scope", "ref": {"finding_key": "a-new-finding"}},
                    q3b / "rulings" / "rulings.jsonl")
    assert got["outcome"] == LF.STOP
    assert any(r["finding_key"] == "a-new-finding" and r["outcome"] == LF.STOP for r in LF.stops(Q3B_SLUG))
    # a STOP row never counts as a removal
    assert all(r["outcome"] != LF.OUTCOME for r in LF.load(q3b) if r["finding_key"] == "a-new-finding")


def test_every_readers_list_lead_is_required_and_ordinary_sentences_are_not():
    for state in ("out_of_scope", "not_material", "not_added_cap", C.NO_PLACE, C.BEYOND, C.OVER_BUDGET):
        line = C.declaration_sentence(state, "A finding the source states.", "A report [1]", None)
        assert LF.is_required_line(line), line
    assert not LF.is_required_line("Removal rose sharply after 2020, the report says.")
    assert not LF.is_required_line("Not added to the total are the soil estimates.")


# ------------------------------------------------------------------ rule 3b provenance (after Q1-04c, fix 1)
# Process doc §4.6.1, "Correction after Q1-04c", second part (advisor's ruling, option (b)).

Q4C = ROOT / "issues" / "WHU-L1-04c-whu-lean-q1-04c"
Q4C_SLUG = "whu-lean-q1-04c"
needs_q4c = pytest.mark.skipif(not (Q4C / "rulings" / "lean_editions.jsonl").exists(),
                               reason="Q1-04c's records are not on this machine")


@needs_q4c
def test_q1_04c_unknown_line_on_a_record_with_no_registries_stops_the_row(lean_on):
    import lean_sentences as LSn
    row = LE.preflight_rows(Q4C_SLUG)[0]
    assert row[0] == LE.ROW and row[1] == LE.BAD, row
    assert "lists no registry searched" in row[2] and "State of CDR 3rd Edition, Chapter 8" in row[2]
    # its line (decided on the fifth freeze, old wording) is still a code line, protected as "reading"
    line = next(d["sentence"] for d in LE.decisions(Q4C) if d.get("outcome") == LE.UNKNOWN_LINE)
    assert LE.is_code_line(line) and B.protected_kind(line) == "reading"
    assert any(line.startswith(x) for x in LSn.LEADS)


def test_unknown_line_names_the_registries_when_the_gate_record_lists_them(tmp_path, monkeypatch):
    import source_store as store
    srcs = _srcs(False)
    st = {"name": "A", "status": "UNKNOWN", "latest_known": "?", "searched": ["Crossref", "Europe PMC"]}
    u = LE.decide("x", tmp_path, st, "S002", srcs, {}, {}, matched_by="identifier (doi)")
    assert u["sentence"] == ("Our recency check (searched: Crossref, Europe PMC) could not establish whether "
                             "The State of Carbon Dioxide Removal, 2nd edition has a newer edition.")
    assert u["searched"] == ["Crossref", "Europe PMC"]
    assert len(SL.sentences(u["sentence"])) == 1 and LE.is_code_line(u["sentence"])
    assert B.protected_kind(u["sentence"]) == "reading"
    # with provenance, the row does not stop on it
    monkeypatch.setattr(store, "case_dir", lambda slug: tmp_path)
    monkeypatch.setattr(LE, "superseded", lambda case: [st])
    row = LE.preflight_rows("x", page_sentences=[u["sentence"]])[0]
    assert row[1] == LE.OK, row
    # without it, the same line on the page stops the row
    v = LE.decide("x", tmp_path / "b", dict(st, searched=[]), "S002", srcs, {}, {}, matched_by="identifier (doi)")
    monkeypatch.setattr(store, "case_dir", lambda slug: tmp_path / "b")
    row = LE.preflight_rows("x", page_sentences=[v["sentence"]])[0]
    assert row[1] == LE.BAD and "lists no registry searched" in row[2]
