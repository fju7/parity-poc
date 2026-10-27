"""Fix 3, step 4: an assessment chapter brings its Summary for Policymakers
(post-study, 2026-10-27; the investigation's option 4). No network: the rule
is run on the committed sources.json of the study issues as a dry run, and the
fetch path with robots.txt and fetch stubbed."""
import json
import os
import shutil
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import acquire_sources as AQ                  # noqa: E402
import coverage_check as C                    # noqa: E402
import judgements as J                        # noqa: E402
import ruling as R                            # noqa: E402
import test_whatholdsup_fix2_coverage as CV   # noqa: E402
import test_whatholdsup_fix3_judgements as T  # noqa: E402

WG2 = "https://www.ipcc.ch/report/ar6/wg2/downloads/report/IPCC_AR6_WGII_SummaryForPolicymakers.pdf"
WG3 = "https://www.ipcc.ch/report/ar6/wg3/downloads/report/IPCC_AR6_WGIII_SPM.pdf"


def _srcs(case_glob):
    return json.loads(next((ROOT / "issues").glob(case_glob + "/sources.json")).read_text())["sources"]


def test_s08_and_s03_would_add_the_wgii_and_wgiii_summaries():
    s8 = AQ.summaries_to_add(_srcs("WHU-S08-*"))
    s3 = AQ.summaries_to_add(_srcs("WHU-S03-*"))
    assert [(e["url"], e["added_for"]) for e in s8] == [(WG2, "S003")]
    assert [(e["url"], e["added_for"]) for e in s3] == [(WG3, "S006")]
    for e in s8 + s3:
        assert e["access"]["state"] == "not_opened" and e["added_by"] == AQ.ADDED_BY
        assert e["licence"]["machine_reading"] and e["licence"]["terms_checked"] is False
        assert e["licence"]["terms"] == "https://www.ipcc.ch/copyright/"
        assert "non-commercial" in e["licence"]["note"] and "not a legal opinion" in e["licence"]["note"]
    assert s8[0]["id"] == "S006" and s3[0]["id"] == "S009"          # the next free ids


def test_an_issue_that_already_holds_the_summary_adds_nothing():
    assert AQ.summaries_to_add(_srcs("WHU-S07-*")) == []


def test_only_ar6_wgii_and_wgiii_chapters_on_the_publishers_site_count():
    srcs = [{"id": "S001", "url": "https://www.ipcc.ch/report/ar6/wg1/downloads/report/IPCC_AR6_WGI_Chapter01.pdf"},
            {"id": "S002", "url": "https://example.org/IPCC_AR6_WGII_Chapter06.pdf"},
            {"id": "S003", "url": "https://www.ipcc.ch/report/ar6/wg2/downloads/report/IPCC_AR6_WGII_Chapter06.pdf"},
            {"id": "S004", "url": "https://www.ipcc.ch/report/ar6/wg2/downloads/report/IPCC_AR6_WGII_Chapter08.pdf"}]
    added = AQ.summaries_to_add(srcs)
    assert [(e["url"], e["added_for"]) for e in added] == [(WG2, "S003")]   # once, not per chapter


@pytest.fixture
def case(tmp_path, monkeypatch):
    import source_store as store
    monkeypatch.setattr(store, "case_dir", lambda slug: tmp_path)
    monkeypatch.setattr(store, "held", lambda slug: {})
    (tmp_path / "sources.json").write_text(json.dumps({"sources": [
        {"id": "S001", "title": "Cities, Settlements and Key Infrastructure",
         "url": "https://www.ipcc.ch/report/ar6/wg2/downloads/report/IPCC_AR6_WGII_Chapter06.pdf",
         "access": {"state": "full_text_held"}}]}))
    return tmp_path


def test_robots_disallow_means_not_fetched(case, monkeypatch):
    fetched = []
    monkeypatch.setattr(AQ, "robots_allow", lambda url, agent="*": (False, "robots.txt disallows it"))
    monkeypatch.setattr(AQ, "fetch", lambda url, timeout=45: fetched.append(url))
    AQ.main(["x", "--only", "S002"])
    srcs = json.loads((case / "sources.json").read_text())["sources"]
    spm = [s for s in srcs if s["id"] == "S002"][0]
    assert spm["url"] == WG2 and spm["access"]["last_fetch"]["why"] == "robots.txt disallows it"
    assert fetched == []


def test_robots_allowed_goes_through_the_normal_fetch_rules(case, monkeypatch):
    tried = []
    monkeypatch.setattr(AQ, "robots_allow", lambda url, agent="*": (True, "robots.txt allows it"))

    def fetch(url, timeout=45):
        tried.append(url)
        raise urllib.error.HTTPError(url, 503, "unavailable", {}, None)
    monkeypatch.setattr(AQ, "fetch", fetch)
    AQ.main(["x", "--only", "S002"])
    assert tried == [WG2]
    spm = [s for s in json.loads((case / "sources.json").read_text())["sources"] if s["id"] == "S002"][0]
    assert "HTTP 503" in spm["access"]["last_fetch"]["why"] and spm["access"]["state"] == "not_opened"


def test_no_summaries_adds_nothing(case, monkeypatch):
    monkeypatch.setattr(AQ, "fetch", lambda url, timeout=45: pytest.fail("no fetch expected"))
    AQ.main(["x", "--only", "S999", "--no-summaries"])
    assert [s["id"] for s in json.loads((case / "sources.json").read_text())["sources"]] == ["S001"]


def test_coverage_reads_an_added_summary():
    srcs = [{"id": "S009", "added_by": AQ.ADDED_BY}]
    assert "S009" in C.relied_on("x", {}, {}, srcs)


# ----------------------------------------------------------------- with the summary held, the check flags

def test_synthetic_twin_an_unstated_relevant_summary_statement_is_flagged(tmp_path):
    held = {"S009": CV.SPM}
    q = "Could investments in public transport and walking support a shift to less intensive modes?"
    scope = {"question": q, "covers": "", "out": []}
    R.rule_judgements("x", T.Lexical(), P=T.P, held=held, scope=scope, case=tmp_path)
    row = dict((r[0], r) for r in J.preflight_rows("x", [], held=held, rows={}, case=tmp_path))[J.ROW]
    assert row[1] == J.BAD and "SPM C.8.2" in row[2]


def _key_quote(q, n):
    p = Path(os.path.expanduser("~/Projects/whu-study-private/keys")) / q / "key.json"
    if not p.exists():
        pytest.skip("the answer keys are private and not here")
    c = [c for c in json.loads(p.read_text())["conclusions"] if c["n"] == n][0]
    return [x for x in c["quotes"] if x["role"] == "conclusion"][0]["text"]


def _held_summary(slug, sid):
    h = R.held_texts(slug)
    if sid not in h:
        pytest.skip("the held summary is not here")
    return h[sid]


@pytest.mark.parametrize("q,n,slug,summary_from", [
    ("WHU-S08", 2, "settlement-planning-climate-resilience", ("city-growth-climate-coping", "S001")),
    ("WHU-S03", 1, "public-involvement-climate-policy", ("urban-form-transport-emissions", "S003")),
])
def test_replay_with_the_summary_held_the_key_conclusion_is_flagged(tmp_path, q, n, slug, summary_from):
    """The summary acquire_sources would add, taken from WHU's own held copy in
    another issue; which statement holds the answer key's conclusion is read
    from the private key at run time, never written here."""
    import audit_stage as A
    import bindings as B
    import premise as PM
    quote = _key_quote(q, n)
    held = dict(R.held_texts(slug))
    if not held:
        pytest.skip("the held texts are not here")
    added = AQ.summaries_to_add(_srcs("WHU-%s-*" % q.split("-")[1]))
    held[added[0]["id"]] = _held_summary(*summary_from)
    R.rule_judgements(slug, T.Lexical(), P=T.P, held=held, scope=PM.scope_of(slug), case=tmp_path)
    at = A.locate(quote[:120], held[added[0]["id"]])
    assert at is not None
    [c] = [c for c in J.candidates({added[0]["id"]: held[added[0]["id"]]}) if c["at"][0] <= at[0] < c["at"][1]]
    e = J.load(tmp_path)["candidates"][c["key"]]
    assert e["relevant"] is True
    st, _ = J.state_of(c, held[c["source"]], B.load(slug)["bindings"], held, {}, {"omissions": []})
    assert st == "not stated"
    row = dict((r[0], r) for r in J.preflight_rows(slug, [], held=held, rows=B.load(slug)["bindings"],
                                                    case=tmp_path))[J.ROW]
    assert row[1] == J.BAD
