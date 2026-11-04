"""The fresh set's stage-1 runner (study/whu-reliability/check_pilot/run_fresh_v8.py) and sample draw
(fresh_samples.py), offline. No model call, no fetch, no ledger write."""
import json
import math
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(ROOT / "study" / "whu-reliability" / "check_pilot"))
import fresh_samples as FS  # noqa: E402
import pipeline_v6 as P6  # noqa: E402
import pipeline_v8 as P8  # noqa: E402
import run_fresh_v8 as F  # noqa: E402

PAIRS = [("WHU-CF-01", "Claude"), ("WHU-CF-01", "Gemini")]


@pytest.fixture
def fresh(tmp_path, monkeypatch):
    """Two answers, private outputs in tmp_path, captures 'verified', samples frozen, an estimate on file."""
    monkeypatch.setattr(F, "OUT", tmp_path)
    monkeypatch.setattr(F, "sample", lambda: list(PAIRS))
    monkeypatch.setattr(F, "do_verify", lambda _a=None: 0)
    monkeypatch.setattr(F, "SAMPLES", tmp_path / "sampling_log.json")
    F.SAMPLES.write_text("{}")
    monkeypatch.setattr(F, "capture", lambda q, s: ("answer text", "claude_sources_r1"))
    rows = [{"answer": "%s/%s" % qs, "likely_usd": 3.0, "worst_usd": 9.0} for qs in PAIRS]
    (tmp_path / "estimate.json").write_text(json.dumps({"at": "t", "likely_usd": 6.0, "worst_usd": 18.0,
                                                        "rows": rows}))
    monkeypatch.setattr(F.R5, "today_total", lambda: 0.0)
    monkeypatch.setattr(F.V1, "prompt_ok", lambda: None)
    return tmp_path


def args(today, vp=0.0):
    return types.SimpleNamespace(today=today, vp_planned=vp)


def test_the_runner_meters_on_its_own_issue_and_role(monkeypatch):
    got = {}
    monkeypatch.setattr(F.S, "metered", lambda raw, **kw: got.update(kw) or raw)
    monkeypatch.setitem(sys.modules, "anthropic", types.SimpleNamespace(Anthropic=lambda **k: object()))
    monkeypatch.setattr(F.J, "env_keys", lambda: {"ANTHROPIC_API_KEY": "x"})
    F.clients()
    assert got["issue"] == "whu-check-fresh-v8" and got["role"] == "check-fresh-v8"
    caps = json.loads((ROOT / "backend" / "data" / "spend" / "caps.json").read_text())
    assert caps["per_issue"]["whu-check-fresh-v8"] == F.LINE_CAP == 75


def test_no_call_without_frozen_samples(fresh, monkeypatch, capsys):
    F.SAMPLES.unlink()
    monkeypatch.setattr(F, "clients", lambda *a, **k: (_ for _ in ()).throw(AssertionError("a client was made")))
    assert F.do_run(args(20)) == 4
    assert "samples are not drawn" in capsys.readouterr().out


def test_likely_over_the_line_cap_calls_nothing(fresh, monkeypatch, capsys):
    monkeypatch.setattr(F, "spent", lambda entries=None: 70.0)              # 70 + likely 6 > 75
    monkeypatch.setattr(F, "clients", lambda *a, **k: (_ for _ in ()).throw(AssertionError("a client was made")))
    assert F.do_run(args(20)) == 5
    assert "nothing was called" in capsys.readouterr().out


def test_no_room_under_the_day_cap_calls_nothing(fresh, monkeypatch):
    monkeypatch.setattr(F, "spent", lambda entries=None: 0.0)
    monkeypatch.setattr(F.R5, "today_total", lambda: 35.0)                  # 35 + 20 leaves 5 < 10
    monkeypatch.setattr(F, "clients", lambda *a, **k: (_ for _ in ()).throw(AssertionError("a client was made")))
    assert F.do_run(args(20)) == 3


def test_an_answer_that_would_pass_todays_amount_is_not_started_and_a_finished_one_is_kept(fresh, monkeypatch):
    ledger = [0.0]
    monkeypatch.setattr(F, "spent", lambda entries=None: ledger[0])
    monkeypatch.setattr(F, "role_lines", lambda entries=None: [])
    monkeypatch.setattr(F, "clients", lambda *a, **k: (object(), types.SimpleNamespace(messages=None)))
    ran = []

    def fake_check(text, w, client, fmt, s, net=None, before_call=None):
        ran.append(s)
        w.mkdir(parents=True, exist_ok=True)
        ledger[0] += 3.5
        return {"results": [], "jobs": [], "seconds": 1.0, "seconds_windows": 0.0, "summary": "", "over_limit": []}
    monkeypatch.setattr(F.P, "check", fake_check)
    assert F.do_run(args(5)) == 0                                            # 3.5 spent + likely 3 > 5
    assert ran == ["Claude"] and (F.work(*PAIRS[0]) / "results.json").exists()
    assert not F.work(*PAIRS[1]).exists()
    assert F.do_run(args(5)) == 0 and ran == ["Claude", "Gemini"]            # next day: the finished one is kept


def test_an_interrupted_answer_is_set_aside_and_not_kept(fresh, monkeypatch):
    monkeypatch.setattr(F, "spent", lambda entries=None: 0.0)
    monkeypatch.setattr(F, "role_lines", lambda entries=None: [])
    monkeypatch.setattr(F, "clients", lambda *a, **k: (object(), types.SimpleNamespace(messages=None)))

    def stops(text, w, *a, **k):
        w.mkdir(parents=True, exist_ok=True)
        raise P8.Stop("cap")
    monkeypatch.setattr(F.P, "check", stops)
    assert F.do_run(args(20)) == 0
    assert not (F.work(*PAIRS[0]) / "results.json").exists()
    monkeypatch.setattr(F.P, "check", lambda text, w, *a, **k: (w.mkdir(parents=True), {
        "results": [], "jobs": [], "seconds": 1.0, "seconds_windows": 0.0, "summary": "", "over_limit": []})[1])
    assert F.do_run(args(20)) == 0
    assert list(fresh.glob("run/*.interrupted-*"))


def test_a_partial_set_is_not_analysed(fresh):
    F.work(*PAIRS[0]).mkdir(parents=True)
    (F.work(*PAIRS[0]) / "results.json").write_text("{}")
    with pytest.raises(P8.Stop, match="partial set"):
        F.compare()


def test_each_mean_is_also_shown_without_the_largest_answer():
    d = F.dist([1.0, 2.0, 9.0])
    assert d["mean"] == 4.0 and d["mean_without_largest"] == 1.5 and d["median"] == 2.0 and d["max"] == 9.0


def test_perplexity_reads_by_the_export_it_is(tmp_path, monkeypatch):
    monkeypatch.setattr(F, "ANSWERS", tmp_path)
    (tmp_path / "Q").mkdir()
    (tmp_path / "Q" / "perplexity.md").write_text("## Report\n\nText [^1].\n\n## References\n\n1. [a](https://a)\n")
    assert F.capture("Q", "Perplexity")[1] == "perplexity_sources"
    (tmp_path / "Q" / "perplexity.md").write_text("## Report\n\nText [^1_1].\n\n[^1_1]: https://a\n")
    assert F.capture("Q", "Perplexity")[1] == "perplexity_footnotes"


def test_the_estimate_prices_a_long_source_once_at_the_chance_one_citing_claim_is_reread(tmp_path):
    (tmp_path / "sources").mkdir()
    long_text = "Paragraph text about the basin survey and its readings.\n\n" * 6000       # ~180k estimated
    (tmp_path / "sources" / "L.txt").write_text(long_text)
    (tmp_path / "sources" / "s.txt").write_text("short source " * 100)
    man = {"https://l": {"source_id": "L", "extent": "full text"}, "https://s": {"source_id": "s", "extent": "full"}}
    claim = lambda u: {"label": None, "n_in": 1000, "worst": 0.1, "citations": [{"url": u, "label": "[1]"}]}
    prep = {"planned": [claim("https://l"), claim("https://l"), claim("https://s")], "claims": [1, 2, 3],
            "manifest": man}
    count = P8.LocalCount()
    rates = {"usd_per_input_token": 5e-6, "reread_share": 0.5}
    est = F.estimate_answer(prep, tmp_path, count, rates)
    ws = P6.windows(long_text, count, size=P8.WINDOW_EST)
    win_in = sum(count(long_text[a:b]) for a, b in ws) + len(ws) * P8.PROMPT_ALLOWANCE
    short_in = count("short source " * 100) + P8.PROMPT_ALLOWANCE
    want = 3000 * 5e-6 + 0.5 * short_in * 5e-6 + (1 - 0.5 ** 2) * win_in * 5e-6
    assert est["long_sources"] == 1 and est["windows"] == len(ws) >= 2
    assert est["likely_usd"] == pytest.approx(want, abs=1e-4)
    assert est["worst_usd"] > est["likely_usd"] and est["worst_usd"] >= 0.3 + P6.worst_cost(short_in)
    assert math.isclose(sum(1 for _ in ws), est["windows"])


def test_samples_are_drawn_once_and_only_before_any_v8_result(fresh, monkeypatch):
    monkeypatch.setattr(FS, "FROZEN", fresh / "frozen.json")
    monkeypatch.setattr(sys, "argv", ["fresh_samples.py", "sample"])
    F.work(*PAIRS[0]).mkdir(parents=True)
    (F.work(*PAIRS[0]) / "results.json").write_text("{}")
    with pytest.raises(SystemExit, match="before any v8 call"):
        FS.main()
    FS.FROZEN.write_text("{}")
    with pytest.raises(SystemExit, match="drawn once"):
        FS.main()


def test_the_seed_is_the_section_16_freeze_commit():
    assert FS.FREEZE == "420f0d654bd1806e7c8f1db28aaceeb179e1089a"
    import fresh_draw as D
    assert D.LABEL % int(FS.FREEZE, 16) == "%d/check-fresh-set" % int(FS.FREEZE, 16)


def test_the_format_record_passes_every_response_on_unchanged():
    pdf = {"status": 200, "body": b"%PDF-1.7 ...", "final_url": "https://x/a.pdf", "content_type": "application/pdf"}
    html = {"status": 200, "body": b"<html>", "final_url": "https://y/", "content_type": "text/html; charset=utf-8"}
    fl = F.FormatLog({"get": lambda u, *a, **k: pdf if "a.pdf" in u else html, "render": lambda u: b"<html>r",
                      "epmc": "kept"})
    net = fl.net()
    assert net["get"]("https://x/a.pdf") is pdf and net["get"]("https://y/") is html
    assert net["render"]("https://z/") == b"<html>r" and net["epmc"] == "kept"
    assert [(r["url"], r["pdf"], r["via"]) for r in fl.rows] == [("https://x/a.pdf", True, "get"),
                                                                  ("https://y/", False, "get"),
                                                                  ("https://z/", False, "render")]
    assert set(F.FormatLog().net()) == set(F.P.V4.V3.NET)                     # every key v8 reads is still there


def test_held_format_and_the_split_by_format():
    fetches = [{"url": "https://x/a.pdf", "final_url": "https://x/a.pdf", "status": 200, "content_type": "",
                "pdf": True},
               {"url": "https://y/", "final_url": "https://y/", "status": 200, "content_type": "text/html"},
               {"url": "https://e/fullTextXML", "final_url": "https://e/fullTextXML", "status": 200,
                "content_type": "application/xml"}]
    man = {"https://x/a.pdf": {"extent": "full text", "retrieved_from": "https://x/a.pdf"},
           "https://y/": {"extent": "full text", "retrieved_from": "https://y/"},
           "https://doi.org/1": {"extent": "full text", "retrieved_from": "https://e/fullTextXML"},
           "https://gone/": {"extent": "unreachable"}}
    assert [F.held_format(man[u], fetches) for u in man] == ["PDF", "HTML", "other", "unreachable"]
    assert F.held_format({"extent": "full text", "retrieved_from": "https://never/"}, fetches) == "unknown"
    cite = lambda *us: [{"url": u} for u in us]
    res = {"manifest": man, "results": [
        {"label": P8.COULDNT, "citations": cite("https://x/a.pdf")},
        {"label": P8.BACKED, "citations": cite("https://x/a.pdf")},
        {"label": P8.BACKED, "citations": cite("https://y/")},
        {"label": P8.NOT_BACKED, "citations": cite("https://y/", "https://x/a.pdf")},
        {"label": P8.COULDNT, "citations": cite("https://gone/")}]}
    out = F.by_format([(res, fetches)])
    assert out["sources"] == {"PDF": 1, "HTML": 1, "other": 1, "unreachable": 1}
    assert out["claims"]["PDF"] == {"claims": 2, "labels": {P8.COULDNT: 1, P8.BACKED: 1}, "couldnt_check_share": 0.5}
    assert out["claims"]["mixed"]["claims"] == 1 and out["claims"]["no source held"]["couldnt_check_share"] == 1.0


def test_answer_cost_is_the_row_sum_not_the_rows_plus_their_breakdowns():
    res = {"results": [{"usd": 1.5, "usd_reread": 0.5}, {"usd": 0.25}], "jobs": [{"usd": 1.0}]}
    assert F.answer_usd(res) == 1.75


def test_the_gate_names_this_issue():
    ok, why = F.gate(10.0, 0.0, F.LINE_CAP)
    assert ok and why.startswith("whu-check-fresh-v8 has spent")
