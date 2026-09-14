"""page_changed_at: the date on the page is when the page changed for readers,
not when somebody ran a command.

Run:  cd backend && python3 -m pytest tests/whatholdsup/test_page_changed_at.py -q

WHY THIS EXISTS
index_dates.publications() dated every card from `at`, the instant a row was
written to published.json. For a row written by the deploy poll that is within
seconds of the truth; for a row written about bytes that were already live it
is a different day. The row now carries page_changed_at (preferred) with a
source saying how it was established; `at` keeps meaning when the row was
written. Every record here is synthetic; every publish/update run below is
stubbed -- no git, no network, no file under site/ is touched.
"""
from __future__ import annotations

import io
import json
import pathlib
import sys
import contextlib
from argparse import Namespace
from datetime import datetime, timezone

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import publish as P            # noqa: E402
import index_dates as I        # noqa: E402

AT = "2026-09-14T19:00:00+00:00"           # when the row was written
CHANGED = "2026-09-13T15:51:05+00:00"      # when the page changed for readers


def _install(monkeypatch, tmp_path, rows):
    rec = tmp_path / "published.json"
    rec.write_text(json.dumps({"what_this_is": "synthetic", "published": rows}))
    monkeypatch.setattr(P, "RECORD", rec)
    monkeypatch.setattr(I, "RECORD", rec)
    return rec


# --- T1 / T2: the preference and the fallback -------------------------------------

def test_T1_page_changed_at_dates_the_card_not_at(monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, [{"issue": "melanoma", "action": "publish", "at": AT,
                                      "sha": "a" * 64, "page_changed_at": CHANGED,
                                      "page_changed_at_source": "test"}])
    assert [d.isoformat() for d in I.publications("melanoma")] == [CHANGED]
    assert I.publication_dates("melanoma") == [I.editorial_date(datetime.fromisoformat(CHANGED))]
    assert I.expected("melanoma")["published"].isoformat() == "2026-09-13"


def test_T2_without_it_the_row_falls_back_to_at(monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, [{"issue": "melanoma", "action": "publish", "at": AT, "sha": "a" * 64}])
    assert [d.isoformat() for d in I.publications("melanoma")] == [AT]
    assert I.publication_instant({"at": AT}) == AT
    assert I.publication_instant({"at": AT, "page_changed_at": CHANGED}) == CHANGED


def test_an_update_row_is_dated_the_same_way(monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, [
        {"issue": "cdk46", "action": "publish", "at": "2026-08-29T02:22:50+00:00", "sha": "a" * 64},
        {"issue": "cdk46", "action": "update", "at": AT, "sha": "b" * 64, "page_changed_at": CHANGED}])
    assert [d.isoformat() for d in I.publications("cdk46")][-1] == CHANGED


# --- T4: the flag records its source; the normal path is the poll --------------------

@pytest.fixture
def publish_stubbed(monkeypatch, tmp_path):
    """cmd_publish / cmd_update with every side effect stubbed: preflight passes,
    git does nothing, the live page already serves the working tree."""
    rec = _install(monkeypatch, tmp_path, [
        {"issue": "melanoma", "action": "publish", "at": "2026-09-10T17:54:52+00:00", "sha": "0" * 64}])
    page = ROOT / P.ISSUES["melanoma"]["page"]
    monkeypatch.setattr(P, "preflight", lambda slug, **kw: [])
    monkeypatch.setattr(P, "show", lambda rows, waive=None, unwaivable=None: True)

    def git(*a):
        if a[:2] == ("rev-parse", "--abbrev-ref"):
            return 0, "main"
        if a[0] == "symbolic-ref":
            return 0, "origin/main"
        if a[0] == "rev-parse":
            return 0, "f" * 40
        return 0, ""                     # status (clean), add, commit, push
    monkeypatch.setattr(P, "git", git)
    monkeypatch.setattr(P, "live_body", lambda url, timeout=20: page.read_text(encoding="utf-8"))
    monkeypatch.setattr(P.time, "sleep", lambda s: None)
    monkeypatch.setattr(P.os.environ, "pop", lambda *a, **k: None)
    return rec


def _rows(rec):
    return json.loads(rec.read_text())["published"]


def _publish(rec, **flags):
    args = Namespace(slug="melanoma", yes=True, waive=None, page_changed_at=None,
                     page_changed_at_evidence=None)
    for k, v in flags.items():
        setattr(args, k, v)
    with contextlib.redirect_stdout(io.StringIO()):
        rc = P.cmd_publish(args)
    return rc, _rows(rec)[-1]


def test_T4_normal_path_records_the_deploy_poll(publish_stubbed):
    before = datetime.now(timezone.utc).replace(microsecond=0)   # the row is recorded to the second
    rc, row = _publish(publish_stubbed)
    assert rc == 0 and row["action"] == "publish"
    assert row["page_changed_at_source"].startswith("deploy-poll:")
    assert "operator" not in row["page_changed_at_source"]
    when = datetime.fromisoformat(row["page_changed_at"])
    assert before <= when <= datetime.now(timezone.utc)
    assert datetime.fromisoformat(row["at"]) >= when          # written after the confirmation


def test_T4_operator_flag_wins_and_records_its_source(publish_stubbed):
    rc, row = _publish(publish_stubbed, page_changed_at=CHANGED,
                       page_changed_at_evidence="Vercel deployment e666318 ready 2026-09-13T15:51:05Z")
    assert rc == 0
    assert row["page_changed_at"] == CHANGED
    assert row["page_changed_at_source"] == (
        "operator-supplied: Vercel deployment e666318 ready 2026-09-13T15:51:05Z")
    assert row["at"] != CHANGED                                # `at` still says when the row was written


def test_T4_the_flag_needs_evidence_and_a_timezone(publish_stubbed):
    with pytest.raises(SystemExit):
        _publish(publish_stubbed, page_changed_at=CHANGED)
    with pytest.raises(SystemExit):
        _publish(publish_stubbed, page_changed_at="2026-09-13T15:51:05",
                 page_changed_at_evidence="x")
    assert len(_rows(publish_stubbed)) == 1                    # nothing appended either time


def test_T4_update_path_carries_the_same_fields(publish_stubbed, monkeypatch):
    args = Namespace(slug="cdk46", yes=True, waive=None, what="a study", changed="two lines",
                     source=None, page_changed_at=None, page_changed_at_evidence=None)
    page = ROOT / P.ISSUES["cdk46"]["page"]
    monkeypatch.setattr(P, "live_body", lambda url, timeout=20: page.read_text(encoding="utf-8"))
    rec = publish_stubbed
    rows = _rows(rec) + [{"issue": "cdk46", "action": "publish", "at": "2026-08-31T16:58:05+00:00", "sha": "1" * 64}]
    rec.write_text(json.dumps({"what_this_is": "synthetic", "published": rows}))
    with contextlib.redirect_stdout(io.StringIO()):
        rc = P.cmd_update(args)
    row = _rows(rec)[-1]
    assert rc == 0 and row["action"] == "update"
    assert row["page_changed_at_source"].startswith("deploy-poll:")
    args.page_changed_at, args.page_changed_at_evidence = CHANGED, "reflog"
    rows = _rows(rec)[:-1]
    rec.write_text(json.dumps({"what_this_is": "synthetic", "published": rows}))
    with contextlib.redirect_stdout(io.StringIO()):
        P.cmd_update(args)
    assert _rows(rec)[-1]["page_changed_at_source"] == "operator-supplied: reflog"


def test_never_a_commit_date():
    src = (W / "publish.py").read_text(encoding="utf-8")
    i = src.index("def page_changed_fields"); body = src[i:src.index("def load_record")]
    assert "%ci" not in body and "%cd" not in body and "committerdate" not in body
