"""An unreadable correction no longer blocks a held source (advisor's ruling 5 on the design review of 2026-11-26;
orchestrator.code_acquire, correction_notes.py, orch/page.Page.render, source_ledger.plain, errata.preflight_rows).

Tested on the recorded 02za and 02zc S003 and S004 -- the evidence-and-gap map (Erratum in 37133285: no text of the
notice could be held) and the Asia-Pacific teacher review (Erratum in 36913230: the notice does not name it). Both
had their own full text held (the trial library's index for 02zc lists PMC8356326 and PMC9700054) and were blocked
by the correction rule alone. Now each stays held, records `correction_unreadable`, and every claim bound to it
carries "This source was corrected; we could not read the correction." An unreadable retraction or expression of
concern still refuses the source. Registry answers are the recorded ones (sources.json retraction_check) and the
recorded notice fixture; nothing is fetched.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(W))
FX = ROOT / "backend/tests/fixtures/whu_orch_corrections"

import correction_notes as CN  # noqa: E402

RUNS = ["WHU-OT1-02za-whu-lean-orch-t1-q1-02za", "WHU-OT1-02zc-whu-lean-orch-t1-q1-02zc"]


def _recorded(folder):
    d = json.loads((ROOT / "issues" / folder / "sources.json").read_text(encoding="utf-8"))
    out = {}
    for s in d["sources"]:
        if s["id"] in ("S003", "S004"):
            line = (s["access"].get("not_held") or {}).get("line")
            assert line in ("correction_not_held", "correction_unread"), (folder, s["id"], line)
            out[s["id"]] = s
    return out


def _case(tmp_path, folder):
    import orchestrator  # noqa: F401
    c = tmp_path / "issues" / folder
    (c / "draft").mkdir(parents=True)
    rec = _recorded(folder)
    held1 = {"id": "S001", "type": "review", "title": "A held review", "used_for": "x",
             "access": {"state": "full_text_held"}}
    srcs = [held1]
    for sid in ("S003", "S004"):
        s = dict(rec[sid])
        s["access"] = {"state": "full_text_held"}            # its own text was held; only the correction rule blocked it
        srcs.append(s)
    (c / "sources.json").write_text(json.dumps({"sources": srcs}))
    return c, rec


def _fake_registries(monkeypatch, rec):
    from orch import corrections as CR
    by_corr = {}
    for sid, s in rec.items():
        by_corr[sid] = s["retraction_check"]["corrections"]
    monkeypatch.setattr(CR, "status", lambda s, *a: {
        "retracted": False, "concern": False, "why": [], "answered": ["Europe PMC", "PubMed", "Crossref"],
        "registries": [], "corrections": by_corr.get(s["id"], [])})
    notice = CR._notice_body((FX / "epmc_fulltext_PMC9968378.xml").read_text())   # names neither source

    def notice_text(c, lookup, fulltext):
        if c["id"] in ("37133285", "10.1002/cl2.1104"):
            return None, "abstract 51 characters; full text not served (recorded)"
        return notice, "recorded"
    monkeypatch.setattr(CR, "notice_text", notice_text)
    from orch import results as RS
    monkeypatch.setattr(RS, "stop_reason", lambda held: None)


@pytest.mark.parametrize("folder", RUNS)
def test_02za_02zc_s003_s004_are_held_with_their_unread_correction_recorded(tmp_path, monkeypatch, folder):
    import orchestrator as O
    c, rec = _case(tmp_path, folder)
    _fake_registries(monkeypatch, rec)
    out = O.code_acquire(SimpleNamespace(case=c, slug="x"), None)
    assert out["outcome"] == "3 held, 0 not held" and out["lines"] == {}
    doc = {s["id"]: s for s in json.loads((c / "sources.json").read_text())["sources"]}
    for sid in ("S003", "S004"):
        want = rec[sid]["access"]["not_held"]["line"]
        assert doc[sid]["access"]["state"] == "full_text_held" and "not_held" not in doc[sid]["access"]
        assert doc[sid]["correction_unreadable"]["line"] == want
    assert set(CN.unread({"sources": list(doc.values())})) == {"S003", "S004"}


def test_an_unreadable_retraction_or_concern_still_refuses(tmp_path, monkeypatch):
    import orchestrator as O
    from orch import corrections as CR
    from orch import results as RS
    c, rec = _case(tmp_path, RUNS[1])
    monkeypatch.setattr(CR, "status", lambda s, *a: {
        "retracted": s["id"] == "S003", "concern": s["id"] == "S004", "why": ["Retraction in 1 (notice unreadable)"],
        "answered": [], "registries": [], "corrections": []})
    monkeypatch.setattr(RS, "stop_reason", lambda held: None)
    with pytest.raises(O.InsufficientSources):
        O.code_acquire(SimpleNamespace(case=c, slug="x"), None)
    doc = {s["id"]: s for s in json.loads((c / "sources.json").read_text())["sources"]}
    assert doc["S003"]["access"]["not_held"]["line"] == "retracted"
    assert doc["S004"]["access"]["not_held"]["line"] == "concern"


def _page_and_bindings(c):
    from orch.page import Page
    claim3 = "The gap map finds most studies measured attendance."
    claim4 = "The teacher review finds training improved attitudes."
    other = "The held review reports gains in reading."
    page = Page({"title": "T", "blocks": [{"tag": "p", "section": "findings",
                                           "sentences": [other, claim3, claim4]}], "provenance": {}})
    (c / "bindings.json").write_text(json.dumps({"bindings": {
        "a": {"sentence": other, "source_id": "S001", "on_page": True},
        "b": {"sentence": claim3, "source_id": "S003", "on_page": True},
        "c": {"sentence": claim4, "source_id": "S001", "also_rests_on": [{"source_id": "S004"}], "on_page": True}}}))
    return page, claim3, claim4, other


def test_every_claim_bound_to_such_a_source_carries_the_note_and_readers_skip_it(tmp_path, monkeypatch):
    import orchestrator as O
    import source_ledger as L
    import source_store as store
    c, rec = _case(tmp_path, RUNS[1])
    _fake_registries(monkeypatch, rec)
    O.code_acquire(SimpleNamespace(case=c, slug="x"), None)
    page, claim3, claim4, other = _page_and_bindings(c)
    notes = CN.noted_sentences(c, page.doc)
    assert notes == {claim3: CN.NOTE, claim4: CN.NOTE}
    html = page.render(notes=notes)
    assert html.count(CN.NOTE) == 2 and (claim3 + " " + CN.SPAN) in html and (claim4 + " " + CN.SPAN) in html
    assert CN.NOTE not in L.plain(html)                              # furniture, never a claim
    assert L.sentences(L.plain(html)) == L.sentences(L.plain(page.render()))
    monkeypatch.setattr(store, "case_dir", lambda slug: c)
    (c / "draft" / "p.html").write_text(html)
    assert CN.preflight_rows("x", c / "draft" / "p.html", "ok", "BLOCKED")[0][1] == "ok"
    (c / "draft" / "p.html").write_text(page.render())               # rendered without the notes
    row = CN.preflight_rows("x", c / "draft" / "p.html", "ok", "BLOCKED")[0]
    assert row[1] == "BLOCKED" and "2 claim(s)" in row[2]


def test_the_note_is_the_ruled_sentence():
    assert CN.NOTE == "This source was corrected; we could not read the correction."
