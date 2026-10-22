"""The paid gate, narrowed to what the free checks cannot decide.

By default factcheck_draft.py runs two roles: SOURCE, over the figures and
quotations whatholdsup/narrow_gate.py marks UNDETERMINED (at most one call per
source, given those claims and nothing of the draft), and RECENCY. EXTRACT,
ADVOCATE, INFERENCE and COVERAGE run only with --full. The report records which
mode ran and which claims SOURCE checked, and a narrow report still satisfies
the preflight page-gate row and findings.py (B15).

Fixtures only. Every model role is replaced by a recorder; nothing here can
reach the API, read an issue directory, or write outside tmp_path.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
FC_PATH = ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py"


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


FC = _load("factcheck_draft_narrow_test", FC_PATH)

DRAFT = ("<html><body><p>The review pooled 14,170 adults.</p>"
         "<p>The effect was -0.43.</p></body></html>")
UNDET = {"id": "n1", "figure": "0.43", "claim": "The effect was -0.43.",
         "attributed_to": "S009: A paper we could not open", "scope": "external",
         "source_id": "S009", "access": "blocked",
         "undetermined_because": "S009 is not in the library"}


@pytest.fixture
def run(tmp_path, monkeypatch):
    """Run main() with every role recorded; returns (calls, report, exit code)."""
    def go(selection, *flags):
        calls = []
        draft = tmp_path / "draft.html"
        draft.write_text(DRAFT, encoding="utf-8")
        report = tmp_path / "draft.html.gate.json"

        def rec(name, value):
            def f(*a, **k):
                calls.append(name)
                return value(*a, **k) if callable(value) else value
            return f
        monkeypatch.setattr(FC, "_spend", None)
        monkeypatch.setattr(FC, "call", rec("API", None))     # never reached
        monkeypatch.setattr(FC, "extract_claims", rec("extract", [dict(UNDET, id="c1")]))
        monkeypatch.setattr(FC, "audit_sources", rec(
            "source", lambda claims, *a, **k: {c["id"]: {"id": c["id"],
                                                         "verdict": "VERIFIED"}
                                               for c in claims}))
        monkeypatch.setattr(FC, "sweep_recency", rec("recency", {"studies": []}))
        monkeypatch.setattr(FC, "advocate", rec("advocate", []))
        monkeypatch.setattr(FC, "inference", rec("inference", []))
        monkeypatch.setattr(FC, "coverage", rec("coverage", {"best_coverage": [],
                                                             "contradictions": []}))
        monkeypatch.setattr(FC, "narrow_selection", rec("select", selection))
        monkeypatch.setattr(FC, "cycle_check", lambda *a, **k: True)
        monkeypatch.setattr(FC, "cycle_record", lambda *a, **k: None)
        monkeypatch.setattr(FC, "annotate_reachability", lambda *a, **k: 0)
        monkeypatch.setattr(FC, "load_decisions", lambda *a, **k: {})
        monkeypatch.setattr(FC, "orphaned", lambda *a, **k: [])
        monkeypatch.setattr(FC, "warn_if_unpinned", lambda: None)
        monkeypatch.setattr(FC, "read_draft", lambda path: "The review pooled 14,170 "
                            "adults. The effect was -0.43. " * 20)
        monkeypatch.setattr(sys, "argv", ["factcheck_draft.py", str(draft),
                                          "--report", str(report)] + list(flags))
        with pytest.raises(SystemExit) as ex:
            FC.main()
        rep = json.loads(report.read_text()) if report.exists() else None
        return calls, rep, ex.value.code
    return go


def test_the_default_run_is_narrow_source_and_recency_only(run):
    calls, rep, code = run({"claims": [UNDET], "considered": 5, "excluded": []})
    assert calls == ["select", "source", "recency"]
    assert not {"extract", "advocate", "inference", "coverage", "API"} & set(calls)
    assert code == 0


def test_an_empty_undetermined_set_makes_no_source_call_and_recency_still_runs(run):
    calls, rep, code = run({"claims": [], "considered": 23, "excluded": []})
    assert calls == ["select", "recency"]
    assert rep["verdicts"] == {} and code == 0


def test_full_restores_every_role(run):
    calls, rep, code = run({"claims": [UNDET]}, "--full")
    assert calls == ["extract", "source", "recency", "advocate", "inference", "coverage"]
    assert "select" not in calls
    assert rep["mode"] == "full" and rep["roles_not_run"] == []


def test_the_report_records_the_mode_and_the_claims_source_checked(run):
    calls, rep, code = run({"claims": [UNDET], "considered": 5,
                            "excluded": [{"why": "attested figure row"}]})
    assert rep["mode"] == "narrow"
    assert rep["roles_run"] == ["source", "recency"]
    assert rep["roles_not_run"] == ["extract", "advocate", "inference", "coverage"]
    assert rep["narrow"]["source_checked"] == ["n1"]
    assert rep["narrow"]["considered"] == 5
    assert rep["claims"][0]["undetermined_because"] == "S009 is not in the library"
    assert rep["passed"] is True and rep["sha256"]


def test_a_selection_that_did_not_run_blocks_and_spends_nothing(run):
    calls, rep, code = run(None)
    assert calls == ["select"] and code == 2 and rep is None


def test_the_source_call_is_given_the_selected_claims_and_not_the_draft(monkeypatch):
    sent = []
    monkeypatch.setattr(FC, "call", lambda system, user, **k: sent.append(user) or [])
    FC.audit_sources([UNDET], "draft")
    assert len(sent) == 1
    assert "-0.43" in sent[0] and "14,170" not in sent[0]


def test_one_source_call_per_source():
    claims = [UNDET, dict(UNDET, id="n2", figure="14170"),
              dict(UNDET, id="n3", attributed_to="S010: another")]
    assert {k: len(v) for k, v in FC.source_groups(claims).items()} == \
        {"S009: A paper we could not open": 2, "S010: another": 1}


def test_render_says_a_role_that_did_not_run_did_not_run():
    text, failed = FC.render([], {}, {"studies": []}, [], [], {}, {},
                             not_run=FC.FULL_ONLY_ROLES)
    assert "FAIRNESS  NOT RUN" in text and "INFERENCE  NOT RUN" in text
    assert "COVERAGE  NOT RUN" in text and not failed


def test_dry_run_plan_lists_calls_and_cost_without_calling():
    lines, est = FC.dry_run_plan({"claims": [], "considered": 23, "excluded": []})
    text = "\n".join(lines)
    assert "claims the source role would receive: 0" in text
    assert "recency" in text and "no source call" in text
    assert est == FC.EST_PER_CALL
    lines, est = FC.dry_run_plan({"claims": [UNDET], "considered": 1})
    assert est == 2 * FC.EST_PER_CALL


# --- preflight's page-gate row and B15 read a narrow report as before --------

P = _load("publish_narrow_test", WHU / "publish.py")
F = _load("findings_narrow_test", WHU / "findings.py")


def narrow_report(target, verdicts=None, passed=True):
    import hashlib
    return {"draft": str(target), "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "sentence_fingerprints": [], "passed": passed, "carried": [],
            "checked_at": "2026-10-17", "model": "m", "mode": "narrow",
            "roles_run": ["source", "recency"],
            "roles_not_run": ["extract", "advocate", "inference", "coverage"],
            "narrow": {"source_checked": list((verdicts or {}).keys())},
            "claims": [dict(UNDET)] if verdicts else [], "verdicts": verdicts or {},
            "recency": {"studies": []}, "objections": [], "inferences": [],
            "coverage": {}}


@pytest.fixture
def page(tmp_path, monkeypatch):
    target = tmp_path / "page.html"
    target.write_text(DRAFT, encoding="utf-8")
    for name in ("registry_overturns", "registry_fact_overturns"):
        monkeypatch.setattr(P, name, lambda *a, **k: set())
    monkeypatch.setattr(P, "acceptance_for", lambda *a, **k: None)
    monkeypatch.setattr(P.fc, "load_decisions", lambda *a, **k: {})
    return target


def write(target, rep):
    target.with_suffix(target.suffix + ".gate.json").write_text(json.dumps(rep))


def test_a_clean_narrow_report_on_this_exact_text_passes_the_page_gate_row(page):
    write(page, narrow_report(page))
    d = P.gate_state(page, "testissue")
    state, detail = d["state"], d["detail"]
    assert state == P.OK and "this exact text" in detail


def test_a_narrow_report_on_other_text_is_not_current(page):
    rep = narrow_report(page)
    rep["sha256"] = "0" * 64
    write(page, rep)
    d = P.gate_state(page, "testissue")
    assert d["fresh"] is False


def test_a_narrow_source_finding_blocks_the_page_gate_and_reaches_b15(page):
    v = {"n1": {"id": "n1", "verdict": "WRONG_VALUE", "found_value": "0.34",
                "note": "the source prints 0.34"}}
    rep = narrow_report(page, verdicts=v, passed=False)
    write(page, rep)
    d = P.gate_state(page, "testissue")
    assert d["state"] == P.BAD
    opened = F.open_findings(rep)
    assert [f["id"] for f in opened] == ["n1"]


# --- narrow_gate.select: what counts as UNDETERMINED ---------------------------

NG = _load("narrow_gate", WHU / "narrow_gate.py")


@pytest.fixture
def lib(tmp_path, monkeypatch):
    held = {"S001": "In total 14 170 adults took part; the effect was -0.43."}
    sources = [{"id": "S001", "title": "Held paper", "access": {"state": "full_text_held"}},
               {"id": "S009", "title": "Blocked paper", "access": {"state": "blocked"}},
               {"id": "S050", "title": "Guideline", "access": {"state": "human_read"},
                "licence_forbids_machine_reading": True}]
    SC = NG.B.__dict__.get("SC") or __import__("spancheck")

    def b2(span, slug, sid, **k):
        if sid not in held:
            return SC.UNDETERMINED, "%s is not in the library" % sid
        return (SC._norm(span).lower() in SC._norm(held[sid]).lower()), "searched"
    monkeypatch.setattr(SC, "b2_present", b2)
    monkeypatch.setattr(NG.store, "sources", lambda slug: sources)
    monkeypatch.setattr(NG.store, "held", lambda slug: {k: {} for k in held})
    monkeypatch.setattr(NG.B.store, "sources", lambda slug: sources)
    rows = {}
    monkeypatch.setattr(NG.B, "load", lambda slug: {"bindings": rows})
    quotes = {"quotations": []}
    import quotations as Q
    monkeypatch.setattr(Q, "load", lambda slug: quotes)
    return rows, quotes


def row(sent, sid, span, **kw):
    r = {"sentence": sent, "on_page": True, "bucket": "context", "source_id": sid,
         "span": span}
    r.update(kw)
    return r


def test_a_figure_in_a_held_span_is_not_sent(lib):
    rows, _ = lib
    rows["a"] = row("The effect was -0.43.", "S001", "the effect was -0.43")
    assert NG.select("t")["claims"] == []


def test_a_figure_resting_on_an_unheld_source_is_sent_with_why(lib):
    rows, _ = lib
    rows["a"] = row("The hazard ratio was 0.72.", "S009", "hazard ratio 0.72")
    got = NG.select("t")["claims"]
    assert [(c["figure"], c["source_id"], c["access"]) for c in got] == \
        [("0.72", "S009", "blocked")]
    assert "not in the library" in got[0]["undetermined_because"]


def test_a_figure_in_no_span_is_left_to_rule_1_not_sent(lib):
    rows, _ = lib
    rows["a"] = row("The hazard ratio was 0.81.", "S009", "hazard ratio 0.72")
    assert NG.select("t")["claims"] == []


def test_an_unbound_row_citing_an_unread_source_is_sent(lib):
    rows, _ = lib
    rows["a"] = row("The hazard ratio was 0.72.", "S009", None)
    assert [c["figure"] for c in NG.select("t")["claims"]] == ["0.72"]


def test_attested_rows_and_licensed_sources_are_never_sent(lib):
    rows, quotes = lib
    rows["a"] = row("Category 2A covers 0.72 of it.", "S050", "covers 0.72",
                    bucket="figure")
    quotes["quotations"] = [{"id": "Q-1", "quote": "a licensed passage of words",
                             "source_id": "S050"}]
    got = NG.select("t")
    assert got["claims"] == []
    assert {x["why"] for x in got["excluded"]} == {
        "attested figure row", "licence forbids machine reading"}


def test_quotations_unheld_are_sent_held_and_sourceless_are_not(lib):
    _, quotes = lib
    quotes["quotations"] = [
        {"id": "Q-1", "quote": "words from the blocked paper itself", "source_id": "S009"},
        {"id": "Q-2", "quote": "words from the held paper itself", "source_id": "S001"},
        {"id": "Q-3", "quote": "words with no recorded source", "source_id": ""}]
    got = NG.select("t")
    assert [c["quotation_id"] for c in got["claims"]] == ["Q-1"]
    assert [x["quotation"] for x in got["excluded"]] == ["Q-3"]


# --- the final narrow gate: only what changed since the last run (2026-10-22) ---

PAGE_BEFORE = {"sentence_shas": ["aaa", "bbb"], "quotations": []}


def _prior(tmp_path, page=PAGE_BEFORE):
    p = tmp_path / "prior.gate.json"
    p.write_text(json.dumps({"sha256": "f" * 64, "mode": "narrow", "claims": [], "verdicts": {},
                             "narrow": ({"page": page} if page is not None else {})}))
    return str(p)


def test_nothing_changed_skips_spends_nothing_and_counts_no_run(run, monkeypatch, tmp_path):
    monkeypatch.setattr(FC, "page_state", lambda slug, text: dict(PAGE_BEFORE))
    calls, rep, code = run({"claims": [dict(UNDET, sentence_sha="aaa")]},
                           "--changed-since", _prior(tmp_path))
    assert code == 0 and rep is None
    assert calls == []                                   # no selection, no call, no recency


def test_only_claims_on_changed_sentences_are_sent(run, monkeypatch, tmp_path):
    now = {"sentence_shas": ["aaa", "ccc"], "quotations": []}
    monkeypatch.setattr(FC, "page_state", lambda slug, text: now)
    sel = {"claims": [dict(UNDET, id="n1", sentence_sha="aaa"), dict(UNDET, id="n2", sentence_sha="ccc")],
           "considered": 2, "excluded": []}
    calls, rep, code = run(sel, "--changed-since", _prior(tmp_path))
    assert code == 0 and "source" in calls
    [cid] = rep["narrow"]["source_checked"]
    assert cid.startswith("f") and cid.endswith("-1") and list(rep["verdicts"]) == [cid]
    assert rep["claims"][0]["selected_as"] == "n2"           # fresh id: findings.py cannot mistake it
    cs = rep["narrow"]["changed_since"]
    assert cs["changed_sentences"] == ["ccc"] and cs["undetermined_on_unchanged_sentences_not_sent"] == 1
    assert rep["narrow"]["page"] == now                  # recorded for the next run


def test_a_report_that_did_not_record_the_page_blocks(run, monkeypatch, tmp_path):
    monkeypatch.setattr(FC, "page_state", lambda slug, text: dict(PAGE_BEFORE))
    calls, rep, code = run({"claims": []}, "--changed-since", _prior(tmp_path, page=None))
    assert code == 2 and calls == [] and rep is None


def test_changed_since_is_refused_with_full(run, tmp_path):
    calls, rep, code = run({"claims": []}, "--full", "--changed-since", _prior(tmp_path))
    assert code == 2 and calls == [] and rep is None


def test_a_new_quotation_counts_as_a_change():
    NG = _load("narrow_gate_changed_t", WHU / "narrow_gate.py")
    s, q = NG.changed({"sentence_shas": ["a"], "quotations": ["x"]},
                      {"sentence_shas": ["a"], "quotations": ["x", "y"]})
    assert s == set() and q == {"y"}
    assert [c["id"] for c in NG.only_changed([{"id": "q1", "quote_key": "y"}, {"id": "q2", "quote_key": "x"}],
                                             s, q)] == ["q1"]
