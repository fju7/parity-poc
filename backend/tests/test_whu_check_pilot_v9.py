"""v9 (study/whu-reliability/check_pilot/pipeline_v9.py, §17), offline: no model, no network. The second read only:
the user-supplied source was dropped (advisor, 2026-11-05)."""
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


def test_the_user_supplied_source_is_gone():
    for name in ("supply_source", "supplied_net", "recheck_with_supplied", "identifier_for"):
        assert not hasattr(V9, name)
