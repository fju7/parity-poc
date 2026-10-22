"""A fetched response is held only if it is the document (2026-10-22).

On WHU-S01, `acquire_sources.py --use-routes` recorded a 2,606-byte Elsevier
linking-hub redirect page as "full text held" for a corrigendum: only article
types were asked whether the bytes are the document, and any other type that
identified itself was promoted. Every response now passes
source_store.held_check -- identity, the substance check `source_store add`
records (classify, by the source's form) and the title in the visible text --
or it is not fetched, with the reason. The redirect page here is a saved
reconstruction of that page's structure (same size, same parts: a <title> of
"Redirecting", a meta refresh, hidden form fields, scripts, the article's name
only inside a script), with the journal, identifiers and address replaced.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
REDIRECT = Path(__file__).resolve().parent / "fixtures" / "whatholdsup" / "elsevier_redirect.html"
TITLE = "Correction to Example Glob Health 2019; 7: e101-09"


def _load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sys.modules[name] = m
    sp.loader.exec_module(m)
    return m


store = _load("source_store", WHU / "source_store.py")
AQ = _load("acquire_sources_t", WHU / "acquire_sources.py")


def _notice_html(n_sentences=20):
    body = " ".join("The authors corrected the figure in the published article and the "
                    "conclusions are unchanged by this correction, number %d." % i
                    for i in range(n_sentences))
    return ("<html><head><title>%s</title></head><body><h1>%s</h1><p>%s</p></body></html>"
            % (TITLE, TITLE, body)).encode()


@pytest.fixture
def issue(tmp_path, monkeypatch):
    case = tmp_path / "issues" / "WHU-S99-xq"
    case.mkdir(parents=True)
    (case / "sources.json").write_text(json.dumps({"sources": [
        {"id": "S017", "type": "corrigendum", "url": "https://example.org/notice", "title": TITLE,
         "access": {"state": "fragment_only"}}]}), encoding="utf-8")
    (case / "access-routes.json").write_text(json.dumps({"sources": {
        "S017": {"routes": [["publisher", 200, "https://linkinghub.example.com/retrieve/pii/S0"]]}}}))
    monkeypatch.setattr(store, "CASES", tmp_path / "issues")
    monkeypatch.setattr(store, "LIB", tmp_path / "library")
    monkeypatch.setattr(AQ, "store", store)
    return case


def _run(case, monkeypatch, reply):
    monkeypatch.setattr(AQ, "fetch", lambda url, timeout=45: (reply, "text/html", url))
    rc = AQ.main(["xq", "--use-routes"])
    src = json.loads((case / "sources.json").read_text())["sources"][0]
    return rc, src


def test_the_saved_redirect_page_is_the_size_it_was():
    assert len(REDIRECT.read_bytes()) == 2606


def test_the_redirect_page_identifies_itself_which_is_why_identity_was_not_enough():
    data = REDIRECT.read_bytes()
    ok, why = store.identifies(data, {"title": TITLE}, "text/html")
    assert ok, why                                           # the old test passed it
    assert store.visible_text(data, "text/html") == ""          # its body shows nothing


def test_a_redirect_page_is_recorded_as_not_fetched_with_the_reason(issue, monkeypatch, capsys):
    rc, src = _run(issue, monkeypatch, REDIRECT.read_bytes())
    assert rc == 1
    acc = src["access"]
    assert acc["state"] == "fragment_only"                   # nothing claimed
    assert "held" not in acc
    lf = acc["last_fetch"]
    assert lf["result"] == "not fetched"
    assert "a redirect page" in lf["why"] and "stub" in lf["why"]
    assert "2606 bytes" in lf["why"]
    assert [t["url"] for t in lf["tried"]] == ["https://linkinghub.example.com/retrieve/pii/S0",
                                               "https://example.org/notice"]
    assert store.held("xq") == {}                            # no bytes stored for it
    out = capsys.readouterr().out
    assert "HUMAN SEARCH LIST" in out and "S017" in out


def test_the_real_notice_is_still_held(issue, monkeypatch):
    rc, src = _run(issue, monkeypatch, _notice_html())
    assert rc == 0
    acc = src["access"]
    assert acc["state"] == "full_text_held"
    assert acc["held"]["kind"] == "document" and "last_fetch" not in acc
    assert "title present" in acc["held"]["identified_by"]
    assert store.held("xq")["S017"]["kind"] == "document"


def test_a_later_good_fetch_clears_the_not_fetched_record(issue, monkeypatch):
    _run(issue, monkeypatch, REDIRECT.read_bytes())
    rc, src = _run(issue, monkeypatch, _notice_html())
    assert rc == 0 and "last_fetch" not in src["access"]


def test_a_document_whose_title_is_only_in_its_markup_is_not_held(issue, monkeypatch):
    body = " ".join("A long paragraph about something else entirely, sentence %d of many." % i
                    for i in range(40))
    page = ("<html><head><title>%s</title><meta name='citation_title' content='%s'></head>"
            "<body><p>%s</p></body></html>" % (TITLE, TITLE, body)).encode()
    rc, src = _run(issue, monkeypatch, page)
    assert rc == 1
    assert "title is not in the document's visible text" in src["access"]["last_fetch"]["why"]


def test_a_challenge_page_is_named_as_one(issue, monkeypatch):
    page = ("<html><head><title>Just a moment...</title></head><body>Checking your browser "
            "before accessing. %s <script>window._cf_chl_opt={}</script>%s</body></html>"
            % (TITLE, " " * 2100)).encode()
    rc, src = _run(issue, monkeypatch, page)
    assert rc == 1
    assert "a challenge page" in src["access"]["last_fetch"]["why"]


@pytest.mark.parametrize("stype,why", [("primary", "landing"), ("guideline", "stub")])
def test_every_type_is_asked_not_only_articles(issue, monkeypatch, stype, why):
    p = issue / "sources.json"
    d = json.loads(p.read_text())
    d["sources"][0]["type"] = stype
    p.write_text(json.dumps(d))
    rc, src = _run(issue, monkeypatch, REDIRECT.read_bytes())
    assert rc == 1 and src["access"]["state"] == "fragment_only"
    assert why in src["access"]["last_fetch"]["why"]
