"""Companion pages and the pre-push guard (2026-10-19).

An issue may publish a page beside its assessment (deskilling's corrections
list). The guard allows it only when its issue's last sign-off lists it and the
bytes on the branch hash to the recorded sha256; anything else that is not a
standing page or a published issue still blocks. Fixtures only: the issue
table, the record, the branch listing and the file bytes are all stubbed."""
import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
spec = importlib.util.spec_from_file_location("guard_published", WHU / "guard_published.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)

PAGE = b"<html>the assessment</html>"
COMP = b"<html>the corrections list</html>"
OTHER = b"<html>another issue</html>"
H = lambda b: hashlib.sha256(b).hexdigest()

ISSUES = {
    "deskilling": {"page": "site/whatholdsup/deskilling.html",
                   "companions": ["site/whatholdsup/deskilling-corrections.html"]},
    "melanoma": {"page": "site/whatholdsup/melanoma.html"},
}
STANDING = ["index.html", "what-this-is.html", "who-pays-for-this.html", "the-rubric.html", "issues.html"]


def _setup(monkeypatch, rows, files, listing=None):
    monkeypatch.setattr(G, "_issues", lambda: ISSUES)
    monkeypatch.setattr(G, "_record", lambda ref: rows)
    monkeypatch.setattr(G, "_known_actions", lambda: ("publish", "republish", "update", "announce", "record-deployed"))
    monkeypatch.setattr(G, "_blob", lambda ref, rel: files.get(rel))
    names = listing if listing is not None else [p for p in files if p.startswith("site/whatholdsup/")]
    monkeypatch.setattr(G, "_git", lambda *a: (0, "\n".join(names)))


def _row(slug, sha, companions=None, action="update"):
    r = {"issue": slug, "action": action, "sha": sha, "at": "2026-10-19T16:00:00+00:00"}
    if companions is not None:
        r["companions"] = companions
    return r


def _files(comp=COMP):
    f = {"site/whatholdsup/deskilling.html": PAGE, "site/whatholdsup/melanoma.html": OTHER,
         "site/whatholdsup/deskilling-corrections.html": comp}
    for n in STANDING:
        f["site/whatholdsup/" + n] = b"<html>standing</html>"
    return f


def _blocks_on(blocking, name):
    return [b for b in blocking if name in b]


def test_a_listed_companion_at_its_signed_off_sha_is_allowed(monkeypatch):
    rows = [_row("melanoma", H(OTHER), action="publish"),
            _row("deskilling", H(PAGE), [{"path": "site/whatholdsup/deskilling-corrections.html", "sha256": H(COMP)}])]
    _setup(monkeypatch, rows, _files())
    blocking, _w = G.check()
    assert blocking == []


def test_an_unlisted_page_still_blocks(monkeypatch):
    rows = [_row("melanoma", H(OTHER), action="publish"), _row("deskilling", H(PAGE))]   # no companions on the row
    _setup(monkeypatch, rows, _files())
    blocking, _w = G.check()
    assert _blocks_on(blocking, "deskilling-corrections.html")
    assert "not a standing" in _blocks_on(blocking, "deskilling-corrections.html")[0]


def test_a_companion_edited_after_publish_blocks(monkeypatch):
    rows = [_row("melanoma", H(OTHER), action="publish"),
            _row("deskilling", H(PAGE), [{"path": "site/whatholdsup/deskilling-corrections.html", "sha256": H(COMP)}])]
    _setup(monkeypatch, rows, _files(comp=COMP + b" edited"))
    blocking, _w = G.check()
    hit = _blocks_on(blocking, "deskilling-corrections.html")
    assert len(hit) == 1 and "changed since it was signed off" in hit[0]


def test_a_companion_whose_issue_has_no_record_blocks(monkeypatch):
    rows = [_row("melanoma", H(OTHER), action="publish")]           # deskilling never published
    _setup(monkeypatch, rows, _files())
    blocking, _w = G.check()
    assert _blocks_on(blocking, "deskilling-corrections.html")


def test_a_companion_listed_on_another_issues_record_does_not_count_for_a_different_file(monkeypatch):
    rows = [_row("melanoma", H(OTHER), [{"path": "site/whatholdsup/melanoma-notes.html", "sha256": "0" * 64}], action="publish"),
            _row("deskilling", H(PAGE))]
    _setup(monkeypatch, rows, _files())
    blocking, _w = G.check()
    assert _blocks_on(blocking, "deskilling-corrections.html")


def test_while_publishing_the_issue_its_declared_companions_pass_and_nothing_else_does(monkeypatch):
    rows = [_row("melanoma", H(OTHER), action="publish"), _row("deskilling", "old" * 21 + "x")]
    files = _files()
    files["site/whatholdsup/stray.html"] = b"<html>stray</html>"
    _setup(monkeypatch, rows, files)
    blocking, _w = G.check(publishing="deskilling")
    assert not _blocks_on(blocking, "deskilling-corrections.html")
    assert _blocks_on(blocking, "stray.html")


def test_publishing_another_issue_does_not_exempt_this_ones_companion(monkeypatch):
    rows = [_row("melanoma", H(OTHER), action="publish"), _row("deskilling", H(PAGE))]
    _setup(monkeypatch, rows, _files())
    blocking, _w = G.check(publishing="melanoma")
    assert _blocks_on(blocking, "deskilling-corrections.html")


def test_standing_pages_and_published_issues_are_unaffected(monkeypatch):
    rows = [_row("melanoma", H(OTHER), action="publish"),
            _row("deskilling", H(PAGE), [{"path": "site/whatholdsup/deskilling-corrections.html", "sha256": H(COMP)}])]
    files = _files()
    _setup(monkeypatch, rows, files)
    assert G.check()[0] == []
    # an edited published page still blocks exactly as before
    files["site/whatholdsup/melanoma.html"] = OTHER + b" edited"
    blocking, _w = G.check()
    assert len(blocking) == 1 and "melanoma" in blocking[0] and "changed since it was published" in blocking[0]


def test_publish_records_the_companions_at_their_current_sha(tmp_path, monkeypatch):
    spec2 = importlib.util.spec_from_file_location("publish_for_companions", WHU / "publish.py")
    P = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(P)
    comp = tmp_path / "site" / "whatholdsup" / "x-corrections.html"
    comp.parent.mkdir(parents=True)
    comp.write_bytes(COMP)
    monkeypatch.setattr(P, "ROOT", tmp_path)
    got = P.companion_record({"companions": ["site/whatholdsup/x-corrections.html"]})
    assert got == [{"path": "site/whatholdsup/x-corrections.html", "sha256": H(COMP)}]
    with pytest.raises(SystemExit):
        P.companion_record({"companions": ["site/whatholdsup/missing.html"]})
    assert P.companion_record({}) == []


def test_deskilling_declares_its_corrections_page_as_a_companion():
    assert G._publish_literal("ISSUES")["deskilling"]["companions"] == ["site/whatholdsup/deskilling-corrections.html"]
