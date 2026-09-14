"""KNOWN_ACTIONS: a record row nobody taught the code about is an error, never an absence.

Run:  cd backend && python3 -m pytest tests/whatholdsup/test_known_actions.py -q

WHY THIS EXISTS
On 2026-09-14 every consumer of published.json filtered rows with an allow-list
(`r["action"] in ("publish", "republish")`), so a row carrying a new action
value would have vanished from the homepage dates, the masthead check, the
board, the pre-push guard and both sign-off paths without a word -- and the
record would have looked more resolved than the site. Each test below drives
ONE consumer against a record that holds one unknown row, and asserts that the
consumer fails loudly: raises publish.UnknownAction (or index_dates'), returns
a blocking row, or -- for the one listing that filters nothing -- flags the row
and exits non-zero. Delete the guard in any one consumer and its test fails.

Every case redirects the record to a temporary copy of the real file plus one
foreign row. Nothing is written to the repository and nothing is fetched.
"""
from __future__ import annotations

import io
import json
import pathlib
import sys
import contextlib
from argparse import Namespace

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import publish as P            # noqa: E402
import index_dates as I        # noqa: E402
import issue_facts as F        # noqa: E402
import guard_published as G    # noqa: E402

REAL = ROOT / "backend" / "data" / "whatholdsup" / "published.json"
# A value nobody has taught the code. NOT "record-deployed": that one was added
# to KNOWN_ACTIONS on 2026-09-14 ahead of its writer, and is tested elsewhere.
FOREIGN = {"issue": "melanoma", "action": "retracted",
           "at": "2026-09-14T17:00:00+00:00", "sha": "0" * 64}


def _real_rows() -> list[dict]:
    return json.loads(REAL.read_text(encoding="utf-8"))["published"]


@pytest.fixture
def tainted(tmp_path, monkeypatch):
    """The real record plus one row with an action outside KNOWN_ACTIONS,
    installed as the record for publish.py, index_dates.py and issue_facts.py."""
    rows = _real_rows() + [dict(FOREIGN)]
    rec = tmp_path / "published.json"
    rec.write_text(json.dumps({"what_this_is": "test", "published": rows}))
    monkeypatch.setattr(P, "RECORD", rec)
    monkeypatch.setattr(I, "RECORD", rec)
    return rows


# --- the vocabulary itself ---------------------------------------------------

def test_known_actions_is_exactly_the_record_plus_the_writers():
    in_record = {r.get("action") for r in _real_rows()}
    written = {"publish", "republish", "update", "announce"}   # cmd_publish, cmd_record_live, cmd_update, cmd_announce
    hand_typed = {"announce_void"}                             # 81bc48e, by hand
    declared_ahead = {"record-deployed"}                       # consumers taught first; writer not yet built
    assert set(P.KNOWN_ACTIONS) == in_record | written | hand_typed | declared_ahead
    assert in_record <= set(P.KNOWN_ACTIONS)
    assert set(P.SIGNOFF_ACTIONS) == {"publish", "republish", "update"}
    assert "record-deployed" not in P.SIGNOFF_ACTIONS


def test_the_three_readers_agree_on_the_set():
    """index_dates and guard_published read the literal out of publish.py's
    source; the three must never drift."""
    assert tuple(I.KNOWN_ACTIONS) == tuple(P.KNOWN_ACTIONS)
    assert tuple(G._known_actions()) == tuple(P.KNOWN_ACTIONS)


def test_rows_by_action_refuses_unknown_wanted():
    with pytest.raises(P.UnknownAction):
        P.rows_by_action([], "melanoma", "retracted")


def test_rows_by_action_names_value_issue_and_at(tainted):
    with pytest.raises(P.UnknownAction) as e:
        P.rows_by_action(tainted, "cdk46", "publish")     # another slug: still refuses
    msg = str(e.value)
    assert "'retracted'" in msg and "'melanoma'" in msg and FOREIGN["at"] in msg


def test_a_row_with_no_action_key_is_unknown():
    with pytest.raises(P.UnknownAction):
        P.rows_by_action([{"issue": "melanoma", "at": "x"}], "melanoma", "publish")


# --- publish.py consumers, one each ------------------------------------------

def test_premise_already_published_fails_loudly(tainted, monkeypatch):
    # The exact expression preflight() passes to premise.preflight_rows. It
    # sits forty rows deep in preflight(), behind gate reports and live
    # fetches, so the expression is exercised here and the CALL SITE is held
    # by the source assertion below: driving the whole preflight to reach one
    # keyword argument would cost a minute and a network round-trip per run.
    with pytest.raises(P.UnknownAction):
        bool(P.rows_by_action(P.load_record(), "melanoma", "publish"))


def test_premise_call_site_uses_the_checked_reader():
    src = (W / "publish.py").read_text(encoding="utf-8")
    i = src.index("premise.preflight_rows(")
    call = src[i:i + 200]
    assert "rows_by_action(load_record(), slug, \"publish\")" in call, call
    assert 'r["action"]' not in call


def test_cmd_status_fails_loudly(tainted, monkeypatch):
    monkeypatch.setattr(P, "live_body", lambda url, timeout=20: None)   # no network
    with pytest.raises(P.UnknownAction), contextlib.redirect_stdout(io.StringIO()):
        P.cmd_status(None)


def test_cmd_record_live_fails_loudly(tainted):
    with pytest.raises(P.UnknownAction), contextlib.redirect_stdout(io.StringIO()):
        P.cmd_record_live(Namespace(slug="melanoma", reason=None, yes=False))


def test_cmd_update_fails_loudly(tainted):
    with pytest.raises(P.UnknownAction), contextlib.redirect_stdout(io.StringIO()):
        P.cmd_update(Namespace(slug="cdk46", reason=None, yes=False, waive=None,
                               source=None))


def test_next_action_fails_loudly(tainted, monkeypatch):
    # Everything upstream of the record passes, so the record is reached.
    monkeypatch.setattr(P, "gate_state", lambda f, slug=None: {"state": P.OK, "outstanding": [], "detail": "", "exists": True})
    monkeypatch.setattr(P, "outside_review", lambda page, slug: (P.OK, ""))
    monkeypatch.setattr(P, "preflight", lambda slug, **kw: [])
    with pytest.raises(P.UnknownAction):
        P.next_action("melanoma")


def test_step_states_fails_loudly(tainted):
    with pytest.raises(P.UnknownAction):
        P._step_states("melanoma")


def test_dashboard_folded_line_fails_loudly(tainted, monkeypatch):
    # The folded "complete" branch is the only place _dashboard_html reads the
    # record itself; reach it with every step done and nothing fetched.
    done = [{"name": n, "why": w, "state": "done", "detail": "", "cmd": "",
             "finds": [], "fold": "", "action": None, "chip": ""} for n, w in P.STEPS]
    monkeypatch.setattr(P, "_step_states", lambda slug: done)
    monkeypatch.setattr(P, "next_action", lambda slug: ("", ""))
    monkeypatch.setattr(P, "live_body", lambda url, timeout=20: None)
    with pytest.raises(P.UnknownAction):
        P._dashboard_html(False)


def test_cmd_log_flags_the_row_and_exits_nonzero(tainted):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = P.cmd_log(None)
    out = buf.getvalue()
    assert rc == 1
    assert "retracted" in out and "?? " in out
    assert out.count("\n  2026-") == len(tainted) - 1          # every known row still listed


# --- index_dates.py / issue_facts.py -------------------------------------------

def test_index_dates_publications_raises(tainted):
    with pytest.raises(I.UnknownAction):
        I.publications("deskilling")


def test_index_dates_reconciliations_raises(tainted):
    with pytest.raises(I.UnknownAction):
        I.reconciliations("deskilling")


def test_index_dates_audit_emits_a_blocking_row(tainted):
    index_html = (ROOT / "site" / "whatholdsup" / "index.html").read_text(encoding="utf-8")
    problems = I.audit(index_html)
    assert problems, "an unreadable record must be a disagreement, not silence"
    assert all("retracted" in p and "melanoma" in p and FOREIGN["at"] in p
               for p in problems)
    rows = I.preflight_rows(index_html)
    assert rows[0][1] == I.BAD


def test_issue_facts_fails_loudly(tainted):
    with pytest.raises(I.UnknownAction):
        F._first_publication_instant("cdk46")
    with pytest.raises(I.UnknownAction):
        F.facts("deskilling")


# --- guard_published.py --------------------------------------------------------

def test_guard_blocks_before_checking_any_page(monkeypatch):
    rows = _real_rows() + [dict(FOREIGN)]
    monkeypatch.setattr(G, "_record", lambda ref: rows)
    calls = []
    monkeypatch.setattr(G, "_blob", lambda ref, rel: calls.append(rel) or b"")
    blocking, warnings = G.check(None, None)
    assert len(blocking) == 1 and "retracted" in blocking[0] \
        and "melanoma" in blocking[0] and FOREIGN["at"] in blocking[0]
    assert calls == [], "no page was hashed against a partly-readable record"


def test_guard_main_refuses_the_push(monkeypatch, capsys):
    rows = _real_rows() + [dict(FOREIGN)]
    monkeypatch.setattr(G, "_record", lambda ref: rows)
    monkeypatch.delenv("WHATHOLDSUP_PUBLISHING", raising=False)
    assert G.main([]) == 1
    assert "PUSH REFUSED" in capsys.readouterr().err
