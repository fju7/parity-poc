"""record-deployed taught to the consumers: observation, never sign-off; and the
guard scoped to the one page being published.

Run:  cd backend && python3 -m pytest tests/whatholdsup/test_reconciliation.py -q

WHY THIS EXISTS
"record-deployed" was added to KNOWN_ACTIONS on 2026-09-14 BEFORE the command
that writes it exists, so that the consumers learn the value first. The rule:
a record-deployed row is an OBSERVATION of bytes on the live site. It never
moves a publication date. But an observation no sign-off covers is an
UNRECONCILED state, and while one exists no provenance line may be derived --
the alternative is "not revised" about a page readers demonstrably saw change.

Every record here is SYNTHETIC. The one test that touches the real repository
replays the 13 September push through the guard, read-only, from commits that
exist in this repository's history.
"""
from __future__ import annotations

import io
import json
import pathlib
import sys
import contextlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[3]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))

import publish as P            # noqa: E402
import index_dates as I        # noqa: E402
import issue_facts as F        # noqa: E402
import issues_page as IP       # noqa: E402
import guard_published as G    # noqa: E402

INDEX_HTML = (ROOT / "site" / "whatholdsup" / "index.html").read_text(encoding="utf-8")
A, B = "a" * 64, "b" * 64
T_PUB, T_OBS = "2026-09-10T17:54:52+00:00", "2026-09-14T18:00:00+00:00"


def _install(monkeypatch, tmp_path, rows):
    rec = tmp_path / "published.json"
    rec.write_text(json.dumps({"what_this_is": "synthetic", "published": rows}))
    monkeypatch.setattr(P, "RECORD", rec)
    monkeypatch.setattr(I, "RECORD", rec)
    return rows


def _pub(slug, sha, at=T_PUB, action="publish"):
    return {"issue": slug, "action": action, "at": at, "sha": sha, "url": "u"}


def _obs(slug, sha, at=T_OBS):
    return {"issue": slug, "action": "record-deployed", "at": at, "sha": sha,
            "sha_source": "live-fetch"}


# --- A: the value is known everywhere, and is not a sign-off anywhere -----------

def test_record_deployed_is_known_and_is_not_a_signoff():
    assert "record-deployed" in P.KNOWN_ACTIONS
    assert "record-deployed" not in P.SIGNOFF_ACTIONS
    assert tuple(I.KNOWN_ACTIONS) == P.KNOWN_ACTIONS
    assert tuple(I.SIGNOFF_ACTIONS) == P.SIGNOFF_ACTIONS
    assert G._known_actions() == P.KNOWN_ACTIONS
    assert I.OBSERVATION_ACTIONS == ("record-deployed",)


def test_signoff_consumers_exclude_it(monkeypatch, tmp_path):
    """cmd_record_live and cmd_update: an issue whose ONLY row is an
    observation has never been published, as far as a sign-off path is
    concerned. The guard's _last agrees."""
    rows = _install(monkeypatch, tmp_path, [_obs("melanoma", A)])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        from argparse import Namespace
        rc1 = P.cmd_record_live(Namespace(slug="melanoma", reason=None, yes=False))
        rc2 = P.cmd_update(Namespace(slug="melanoma", reason=None, yes=False, waive=None, source=None))
    assert rc1 == 2 and rc2 == 2 and "never been published" in buf.getvalue()
    assert G._last(rows, "melanoma", "publish") is None
    assert I.publications("melanoma") == []
    assert F._first_publication_instant("melanoma") is None


# --- B1 / T1: never moves a date ---------------------------------------------------

def test_T1_observation_moves_no_publication_date(monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, [_pub("melanoma", A), _obs("melanoma", A)])
    assert [d.isoformat() for d in I.publications("melanoma")] == [T_PUB]
    exp = I.expected("melanoma")                      # "corrected" comes from corrections.md on disk
    assert exp["published"] == I.publication_dates("melanoma")[0] and "updated" not in exp
    # Even an observation of DIFFERENT bytes adds no date -- it adds a refusal.
    _install(monkeypatch, tmp_path, [_pub("melanoma", A), _obs("melanoma", B)])
    assert [d.isoformat() for d in I.publications("melanoma")] == [T_PUB]
    assert I.reconciliations("melanoma") == []


# --- B2 / T2 / T3: the query ------------------------------------------------------

def test_T2_unreconciled_when_observed_differs_from_newest_signoff(monkeypatch, tmp_path):
    rows = _install(monkeypatch, tmp_path, [_pub("melanoma", A), _obs("melanoma", B)])
    u = I.unreconciled_state(rows, "melanoma")
    assert u == {"slug": "melanoma", "observed_sha": B, "observed_at": T_OBS,
                 "signoff_sha": A, "signoff_at": T_PUB, "signoff_action": "publish"}
    assert I.unreconciled("melanoma") == u


def test_T3_reconciled_when_observed_equals_newest_signoff(monkeypatch, tmp_path):
    rows = _install(monkeypatch, tmp_path, [_pub("melanoma", A), _obs("melanoma", A)])
    assert I.unreconciled_state(rows, "melanoma") is None
    assert I.unreconciled("melanoma") is None
    assert not [p for p in I.audit(INDEX_HTML) if I.UNRECONCILED in p and "melanoma" in p]


def test_newest_signoff_wins_not_newest_publish(monkeypatch, tmp_path):
    """A republish/update after the publish is the sign-off that counts."""
    rows = [_pub("melanoma", A), _pub("melanoma", B, "2026-09-11T00:00:00+00:00", "update"),
            _obs("melanoma", B)]
    assert I.unreconciled_state(rows, "melanoma") is None
    rows = [_pub("melanoma", B), _pub("melanoma", A, "2026-09-11T00:00:00+00:00", "republish"),
            _obs("melanoma", B)]
    assert I.unreconciled_state(rows, "melanoma")["signoff_sha"] == A


def test_observation_with_no_signoff_at_all_is_unreconciled():
    u = I.unreconciled_state([_obs("melanoma", B)], "melanoma")
    assert u and u["signoff_sha"] is None and u["observed_sha"] == B


def test_newest_observation_is_the_one_that_counts():
    rows = [_pub("melanoma", A), _obs("melanoma", B, "2026-09-12T00:00:00+00:00"), _obs("melanoma", A)]
    assert I.unreconciled_state(rows, "melanoma") is None          # returned to signed-off bytes
    rows = [_pub("melanoma", A), _obs("melanoma", A, "2026-09-12T00:00:00+00:00"), _obs("melanoma", B)]
    assert I.unreconciled_state(rows, "melanoma")["observed_sha"] == B


# --- B3 / T2: what refuses -----------------------------------------------------------

def test_T2_audit_blocks_and_preflight_is_BAD(monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, [_pub("melanoma", A), _obs("melanoma", B)])
    problems = [p for p in I.audit(INDEX_HTML) if p.startswith("melanoma [%s]" % I.UNRECONCILED)]
    assert len(problems) == 1
    assert A[:8] in problems[0] and B[:8] in problems[0] and T_OBS[:19] in problems[0]
    rows = I.preflight_rows(INDEX_HTML)
    assert rows[0][1] == I.BAD and "UNRECONCILED" in rows[0][2]


def test_T2_facts_and_line_refuse(monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, [_pub("melanoma", A), _obs("melanoma", B)])
    with pytest.raises(I.Unreconciled) as e:
        F.facts("melanoma")
    assert A[:8] in str(e.value) and B[:8] in str(e.value) and "What would have to change" in str(e.value)
    with pytest.raises(I.Unreconciled):
        F.line("melanoma", "Issue one")
    # Other slugs still derive: the refusal is per slug.
    assert F.facts("cdk46")["published"] is None


def test_T2_issues_page_refuses_to_write(monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, [_pub("melanoma", A), _obs("melanoma", B)])
    out = tmp_path / "issues.html"
    monkeypatch.setattr(IP, "OUT", out)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = IP.main()
    assert rc == 1 and not out.exists()
    assert "REFUSED" in buf.getvalue() and "What would have to change" in buf.getvalue()


def test_issue_facts_main_reports_refusal_and_exits_nonzero(monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, [_pub("melanoma", A), _obs("melanoma", B)])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = F.main()
    assert rc == 1 and "REFUSED" in buf.getvalue()


# --- C1: the guard stands aside for ONE page ----------------------------------------

def test_guard_exempts_only_the_published_slug(monkeypatch):
    rows = [_pub("melanoma", A), _pub("deskilling", A), _pub("cdk46", A)]
    monkeypatch.setattr(G, "_record", lambda ref: rows)
    # every page differs, and the push CREATES the difference (remote had "old")
    monkeypatch.setattr(G, "_blob", lambda ref, rel: b"changed" if ref == "ref" else b"old")
    monkeypatch.setattr(G, "_git", lambda *a: (0, ""))                     # no ls-tree listing
    blocking, _ = G.check("ref", "against", publishing="cdk46")
    names = sorted(b.split(":")[0] for b in blocking)
    assert names == ["deskilling", "melanoma"], blocking


def test_guard_first_publish_of_the_named_slug_is_not_an_unpublished_page(monkeypatch):
    rows = [_pub("melanoma", A)]
    monkeypatch.setattr(G, "_record", lambda ref: rows)
    monkeypatch.setattr(G, "_blob", lambda ref, rel: b"x")
    monkeypatch.setattr(G, "_git", lambda *a: (0, "site/whatholdsup/deskilling.html\n"))
    blocking, _ = G.check("ref", None, publishing="deskilling")
    assert not [b for b in blocking if "deskilling.html" in b]
    blocking, _ = G.check("ref", None, publishing=None)
    assert [b for b in blocking if "deskilling.html" in b]


def test_guard_main_never_stands_aside_for_the_old_marker(monkeypatch, capsys):
    seen = {}
    monkeypatch.setattr(G, "check", lambda ref, against, publishing=None: seen.update(p=publishing) or ([], []))
    monkeypatch.setenv("WHATHOLDSUP_PUBLISHING", "1")
    assert G.main(["--quiet"]) == 0 and seen["p"] is None
    assert "names no issue; nothing is exempt" in capsys.readouterr().err
    monkeypatch.setenv("WHATHOLDSUP_PUBLISHING", "cdk46")
    assert G.main(["--quiet"]) == 0 and seen["p"] == "cdk46"


def test_publish_and_update_name_the_slug_not_1():
    src = (W / "publish.py").read_text(encoding="utf-8")
    assert 'os.environ["WHATHOLDSUP_PUBLISHING"] = "1"' not in src
    assert src.count('os.environ["WHATHOLDSUP_PUBLISHING"] = args.slug') == 2


def test_the_13_september_push_would_have_been_blocked():
    """Read-only replay against real history: origin/main moved 5d602ab ->
    e666318 with WHATHOLDSUP_PUBLISHING set by `update cdk46`. Under the
    old marker the guard did not run. Under the scoped one it blocks."""
    blocking, _ = G.check("e666318", "5d602ab", "cdk46")
    names = sorted(b.split(":")[0] for b in blocking)
    assert names == ["deskilling", "melanoma"], blocking
    assert all("has changed since it was published" in b for b in blocking)


# --- C2: wording for the third state, kept apart from known_divergences.json -------

def _guard_rows_and_blobs(monkeypatch, content=b"live-bytes"):
    import hashlib
    now = hashlib.sha256(content).hexdigest()
    rows = [_pub("melanoma", A), _obs("melanoma", now)]
    monkeypatch.setattr(G, "_record", lambda ref: rows)
    monkeypatch.setattr(G, "_blob", lambda ref, rel: content if rel.endswith("melanoma.html") else None)
    monkeypatch.setattr(G, "_git", lambda *a: (0, ""))
    return now


def test_guard_says_recorded_as_observed_not_signed_off(monkeypatch):
    now = _guard_rows_and_blobs(monkeypatch)
    monkeypatch.setattr(G, "_acknowledged", lambda slug: {})
    blocking, warnings = G.check("ref", "against", None)
    assert not blocking
    w = [x for x in warnings if x.startswith("melanoma: site/whatholdsup/melanoma.html")]
    assert len(w) == 1
    assert "recorded as observed on %s; not signed off" % T_OBS[:10] in w[0]
    assert "unrecorded version" not in w[0] and "KNOWN AND UNPUBLISHED" not in w[0]


def test_observation_and_acknowledgement_are_separate_facts(monkeypatch):
    now = _guard_rows_and_blobs(monkeypatch)
    monkeypatch.setattr(G, "_acknowledged", lambda slug: {now: {"on": "2026-09-14", "reason": "left"}})
    _, warnings = G.check("ref", "against", None)
    mine = [x for x in warnings if x.startswith("melanoma: site/whatholdsup/melanoma.html")]
    assert len(mine) == 2                                   # both print; neither implies the other
    assert any("KNOWN AND UNPUBLISHED" in x for x in mine)
    assert any("recorded as observed" in x for x in mine)


def test_observation_of_other_bytes_does_not_cover_these(monkeypatch):
    """The wording is bound to content, like the acknowledgement: an
    observation of some earlier bytes says nothing about the bytes live now."""
    _guard_rows_and_blobs(monkeypatch)
    rows = [_pub("melanoma", A), _obs("melanoma", B)]
    monkeypatch.setattr(G, "_record", lambda ref: rows)
    monkeypatch.setattr(G, "_acknowledged", lambda slug: {})
    _, warnings = G.check("ref", "against", None)
    w = [x for x in warnings if x.startswith("melanoma: site/whatholdsup/melanoma.html")]
    assert len(w) == 1 and "unrecorded version" in w[0]
