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


# ------------------------------------------------------------------ rule 3b

NEW = "State of CDR, 3rd edition. Total removal is about 2.2 GtCO2 a year. Novel removal is small."
OLD = "State of CDR, 2nd edition. Total removal is about 2 GtCO2 a year. Novel removal is small."
STUDY = {"name": "State of CDR 2nd ed.", "status": "SUPERSEDED", "latest_known": "3rd Edition, June 2026"}


def _srcs(with_new: bool):
    s = [{"id": "S002", "title": "The State of Carbon Dioxide Removal, 2nd edition"}]
    if with_new:
        s.append({"id": "S004", "title": "The State of Carbon Dioxide Removal, 3rd edition",
                  "newer_edition_of": "S002"})
    return s


def test_rule3b_the_newer_edition_is_used_when_held_and_every_span_reverifies(tmp_path, monkeypatch):
    import source_store as store
    monkeypatch.setattr(store, "held", lambda slug: {"S004": {"sha256": "new"}})
    rows = {"r1": {"on_page": True, "source_id": "S002", "span": "Novel removal is small.", "document_sha": "old"}}
    saved = []
    d = LE.decide("x", tmp_path, STUDY, "S002", _srcs(True), rows, {"S002": OLD, "S004": NEW}, saved.append)
    assert d["outcome"] == LE.USED and rows["r1"]["source_id"] == "S004" and rows["r1"]["rebound_from"] == "S002"
    assert rows["r1"]["document_sha"] == "new" and saved
    f = {"id": "f1-rec-1"}
    LE.settle_finding(f, d)
    assert f["decision"] == "accepted" and f["source_id"] == "S004" and f["quote"] == "Novel removal is small."


def test_rule3b_otherwise_the_page_discloses_it_and_nothing_is_dropped(tmp_path):
    rows = {"r1": {"on_page": True, "source_id": "S002", "span": "Total removal is about 2 GtCO2 a year."}}
    d = LE.decide("x", tmp_path, STUDY, "S002", _srcs(True), rows, {"S002": OLD, "S004": NEW})
    assert d["outcome"] == LE.DISCLOSED and rows["r1"]["source_id"] == "S002"
    assert d["sentence"] == ("A newer edition exists: 3rd Edition, June 2026; this page uses "
                             "The State of Carbon Dioxide Removal, 2nd edition.")
    assert "not in the newer edition" in d["not_used_because"]
    f = {"id": "f1-rec-1"}
    LE.settle_finding(f, d)
    assert f["decision"] == "judgement" and d["sentence"] in f["why"] and f["by"] == LE.BY
    # decided once: a re-filed finding gets the same decision, no second line
    assert LE.decide("x", tmp_path, STUDY, "S002", _srcs(True), rows, {})["at"] == d["at"]
    assert [x["sentence"] for x in LE.lines(tmp_path)] == [d["sentence"]]
    # unmatched: the gate's study name stands in for the edition
    d2 = LE.decide("x", tmp_path, dict(STUDY, latest_known="4th"), None, _srcs(False), {}, {})
    assert d2["sentence"].endswith("this page uses State of CDR 2nd ed.")


def test_rule3b_the_line_is_generated_protected_and_required():
    line = "A newer edition exists: 3rd Edition, June 2026; this page uses The State of CDR, 2nd edition."
    gen = LS.generate({"question": "Q?"}, [], editions=[{"key": "k", "sentence": line}])
    g = [x for x in gen if x["sentence"] == line][0]
    assert g["kind"] == "reading" and LS.is_framed(line)
    assert B.protected_kind(line.replace("June", "found in June")) == "reading"
    assert LF.required_removed(gen, {LS.words(line)}) == [g]


def test_rule3b_lean_gate_settles_superseded_studies_by_code(tmp_path, monkeypatch, lean_on):
    import findings as F
    import source_store as store
    monkeypatch.setattr(store, "case_dir", lambda slug: tmp_path)
    (tmp_path / "sources.json").write_text(json.dumps({"sources": _srcs(False)}))
    monkeypatch.setattr(F, "recency_targets", lambda slug, study, rows: ([], []))
    report = {"recency": {"studies": [STUDY, {"name": "IPCC", "status": "CURRENT"}]}}
    doc = {"findings": [{"id": "f1234abcd-rec-1", "kind": "recency"}]}
    done = []
    ids = R.lean_editions_gate("x", report, doc, {}, {}, done, write_rows=lambda r: None)
    assert ids == {"f1234abcd-rec-1"} and doc["findings"][0]["decision"] == "judgement"
    assert LE.lines(tmp_path)[0]["sentence"].startswith("A newer edition exists: 3rd Edition, June 2026")
