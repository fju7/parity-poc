"""v9 (study/whu-reliability/check_pilot/pipeline_v9.py, §17), offline: no model, no network."""
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(ROOT / "study" / "whu-reliability" / "check_pilot"))
import pipeline_v9 as V9  # noqa: E402

GOOD = '{"may_overstate": true, "how": "more_certain", "reason": "The passage reports low-certainty evidence; the claim states it as established."}'
NO = '{"may_overstate": false, "how": "none", "reason": "The passage reports the same effect for the same group."}'


def _row(idx, label="BACKED", url="https://a"):
    return {"idx": idx, "claim": "Exercise lowers BMI in teenagers.", "context": "SECRET CONTEXT", "label": label,
            "reason": "SECRET REASON", "passage": {"quote": "a small benefit, low-certainty evidence"},
            "citations": [{"url": url}]}


def _calls(*replies):
    seen = []

    def call(text):
        seen.append(text)
        r = replies[min(len(seen), len(replies)) - 1]
        if isinstance(r, Exception):
            raise r
        return r, {"input": 1, "output": 1}, 0.01, False
    return call, seen


def test_a_flag_shows_may_overstate_with_its_reason_and_keeps_v8s_verdict():
    rows = [_row(0)]
    call, _ = _calls(GOOD)
    V9.apply_second_read(rows, call)
    r = rows[0]
    assert r["shown"] == V9.MAY_OVERSTATE and r["shown_reason"].startswith("The passage reports low-certainty")
    assert r["label"] == "BACKED" and r["passage"]["quote"] == "a small benefit, low-certainty evidence"
    assert r["reason"] == "SECRET REASON"
    assert r["second_read"]["prompt_sha256"] == V9.PROMPT_SHA256 and r["second_read"]["how"] == "more_certain"


def test_only_backed_rows_are_read_and_the_call_sees_only_the_claim_and_passage():
    rows = [_row(0), _row(1, "NOT BACKED"), _row(2, "COULDN'T CHECK")]
    call, seen = _calls(NO)
    V9.apply_second_read(rows, call)
    assert len(seen) == 1 and "second_read" not in rows[1] and "second_read" not in rows[2]
    assert "Exercise lowers BMI" in seen[0] and "low-certainty evidence" in seen[0]
    assert "SECRET" not in seen[0] and "https://a" not in seen[0]
    assert rows[0]["shown"] == "BACKED"


def test_a_malformed_reply_is_retried_once_then_shown_not_done_and_scored_couldnt_check():
    rows = [_row(0)]
    call, seen = _calls("Sure! It overstates.", '{"may_overstate": true, "how": "none", "reason": "x"}')
    V9.apply_second_read(rows, call)
    assert len(seen) == 2 and rows[0]["shown"] == V9.NOT_DONE and not rows[0]["second_read"]["done"]
    assert V9.score_label(rows[0]) == V9.COULDNT


def test_an_api_error_then_a_good_reply_is_done():
    rows = [_row(0)]
    call, seen = _calls(RuntimeError("timeout"), GOOD)
    V9.apply_second_read(rows, call)
    assert len(seen) == 2 and rows[0]["shown"] == V9.MAY_OVERSTATE


def test_out_of_credit_stops_rather_than_counting_as_a_failed_read():
    call, _ = _calls(V9.J.OutOfCredit("credit"))
    with pytest.raises(V9.J.OutOfCredit):
        V9.second_read("c", "p", call)


@pytest.mark.parametrize("reply,ok", [
    (GOOD, True), (NO, True),
    ('{"may_overstate": "yes", "how": "overstates", "reason": "r"}', False),
    ('{"may_overstate": true, "how": "exaggerates", "reason": "r"}', False),
    ('{"may_overstate": false, "how": "overstates", "reason": "r"}', False),
    ('{"may_overstate": true, "how": "overstates", "reason": "r", "extra": 1}', False),
    ('{"may_overstate": true, "how": "overstates", "reason": "%s"}' % ("word " * 26).strip(), False),
])
def test_the_reply_form_is_exact(reply, ok):
    assert (V9.parse_reply(reply)[0] is not None) == ok


def test_score_label_follows_the_table_decided_before_any_call():
    done = lambda mo: {"done": True, "may_overstate": mo, "how": "overstates" if mo else "none", "reason": "r"}
    assert V9.score_label({"label": "BACKED", "second_read": done(False)}) == V9.BACKED
    assert V9.score_label({"label": "BACKED", "second_read": done(True)}) == V9.NOT_BACKED
    assert V9.score_label({"label": "BACKED", "second_read": {"done": False}}) == V9.COULDNT
    for lab in ("NOT BACKED", "COULDN'T CHECK", "NOT FOUND", "NO SOURCE"):
        assert V9.score_label({"label": lab}) == lab


@pytest.mark.parametrize("url,ref,want", [
    ("https://doi.org/10.1002/14651858.CD015330.pub2", "", ("10.1002/14651858.CD015330.pub2", "url")),
    ("https://onlinelibrary.wiley.com/doi/full/10.1111/obr.13000/full", "", ("10.1111/obr.13000", "url")),
    ("https://pubmed.ncbi.nlm.nih.gov/38763518/", "", ("PMID:38763518", "url")),
    ("https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1234567/", "", ("PMC1234567", "url")),
    ("https://www.oecd.org/report.pdf", "Smith J. Title. Lancet. doi:10.1016/S0140-6736(20)30001-1.",
     ("10.1016/S0140-6736(20)30001-1", "reference")),
    ("https://www.oecd.org/report.pdf", "OECD (2023), Some report, OECD Publishing.", (None, "none")),
])
def test_the_identifier_comes_from_the_url_then_the_reference(url, ref, want):
    assert V9.identifier_for(url, ref) == want


def test_an_upload_with_no_identifier_is_refused_before_any_registry_call(tmp_path):
    f = tmp_path / "doc.html"
    f.write_text("<title>A report</title>")
    called = []
    rec = V9.supply_source(f, "https://www.oecd.org/x", "OECD (2023)", "user", tmp_path / "run",
                           supply=lambda *a, **k: called.append(1))
    assert rec["status"] == "REFUSED_NO_IDENTIFIER" and not rec["admitted"] and not called
    assert json.loads((tmp_path / "run" / "supplied" / (rec["sha256"] + ".json")).read_text())["admitted"] is False


def _real_supplied(monkeypatch, title):
    sup = V9._supplied_module()
    from verify import literature
    from verify.types import Exists, Resolution
    monkeypatch.setattr(literature, "resolve", lambda i: Resolution(i, Exists.EXISTS, heading=title,
                                                                    registry="crossref", checked_at="t"))
    monkeypatch.setattr(sup, "_store", lambda *a, **k: (_ for _ in ()).throw(AssertionError("Signal store written")))
    monkeypatch.setattr(sup, "INDEX", Path("/nonexistent/should/not/be/touched/index.json"))
    return sup


def test_the_identity_check_is_verify_supplied_with_store_false_and_never_writes_signals_corpus(tmp_path,
                                                                                               monkeypatch):
    _real_supplied(monkeypatch, "Dietary and physical activity interventions to prevent obesity in adolescents")
    f = tmp_path / "doc.html"
    f.write_text("<html><head><title>Dietary and physical activity interventions to prevent obesity in "
                 "adolescents</title></head><body><p>Body text of the review, long enough to read.</p></body></html>")
    ok = V9.supply_source(f, "https://doi.org/10.1002/14651858.CD015330.pub2", "", "user", tmp_path / "run")
    assert ok["admitted"] and ok["status"] == "ADMITTED" and ok["identifier"] == "10.1002/14651858.CD015330.pub2"
    g = tmp_path / "wrong.html"
    g.write_text("<html><head><title>Screen time and sleep in toddlers: a cohort study</title></head>"
                 "<body><p>Another paper entirely.</p></body></html>")
    bad = V9.supply_source(g, "https://doi.org/10.1002/14651858.CD015330.pub2", "", "user", tmp_path / "run")
    assert not bad["admitted"] and bad["status"] == "REFUSED_HEADING"
    assert "Body text" not in (tmp_path / "run" / "supplied" / (ok["sha256"] + ".json")).read_text()


def test_an_admitted_file_is_served_only_for_its_own_url(tmp_path):
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.7 supplied bytes")
    base = {"get": lambda url, *a, **k: {"status": 403, "final_url": url, "content_type": "text/html", "body": b"wall"}}
    net = V9.supplied_net(base, {"https://a": {"path": str(f)}})
    assert net["get"]("https://a")["body"] == b"%PDF-1.7 supplied bytes" and net["get"]("https://a")["status"] == 200
    assert net["get"]("https://b")["status"] == 403


def test_recheck_marks_only_the_claims_citing_the_admitted_url(tmp_path, monkeypatch):
    prev = {"results": [_row(0, "COULDN'T CHECK", "https://a"), _row(1, "BACKED", "https://b")], "manifest": {}}
    got = {}

    def fake_check(text, work, client, net=None, selected=None, **kw):
        got["selected"], got["body"] = selected, net["get"]("https://a")["body"]
        return {"results": [_row(0, "NOT BACKED", "https://a")], "manifest": {"https://a": {"extent": "full text"}},
                "seconds": 1.0}
    monkeypatch.setattr(V9.P8, "check", fake_check)
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.7 x")
    recs = [{"url": "https://a", "admitted": True, "path": str(f), "sha256": "s", "identifier": "PMC1",
             "supplied_by": "user"}, {"url": "https://b", "admitted": False}]
    out = V9.recheck_with_supplied("answer", tmp_path, None, _calls(NO)[0], prev, recs,
                                   net={"get": lambda u, *a, **k: {}})
    assert got["selected"] == [0] and got["body"] == b"%PDF-1.7 x"
    r0, r1 = out["results"]
    assert r0["label"] == "NOT BACKED" and r0["note"] == V9.SUPPLIED_NOTE and r0["supplied"][0]["sha256"] == "s"
    assert r1 is prev["results"][1] and "note" not in r1


def test_the_replay_stops_before_any_call_without_a_budget_line(monkeypatch, capsys):
    import run_v9_replay as RP
    monkeypatch.setattr(RP.S, "caps", lambda: {"per_issue": {}, "default_per_day": 60})
    monkeypatch.setattr(RP, "backed_rows", lambda: (_ for _ in ()).throw(AssertionError("read rows")))
    boom = lambda text: (_ for _ in ()).throw(AssertionError("called"))
    assert RP.do_run(types.SimpleNamespace(today=5, vp_planned=0), call=boom) == 5
    assert "nothing was called" in capsys.readouterr().out


def test_the_replay_estimate_prices_every_backed_row_with_one_retry_in_the_worst_case():
    import run_v9_replay as RP
    est = RP.estimate([("Q", "S", _row(0)), ("Q", "S", _row(1))])
    assert est["calls"] == 2 and est["worst_usd"] > 10 * est["likely_usd"] > 0
    one = RP.call_usd(V9.second_read_input(_row(0)["claim"], _row(0)["passage"]["quote"]), V9.SECOND_READ_MAX_OUT)
    assert est["worst_usd"] == pytest.approx(2 * 2 * one, abs=1e-4)
