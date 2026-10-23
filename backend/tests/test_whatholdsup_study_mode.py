"""Study mode (protocol rev 27, "The frozen WHU process").

(a) An issue registered by its own issue.json ("study": true) runs `check`, the
    preflight and the audit stage without an entry in publish.ISSUES and
    without email files; `publish`, `update` and `announce` refuse it.
(b) Its preflight records outside review, adjudication verification, operator
    acceptance and publication as SKIPPED with the protocol's reason, and
    never reaches the live site.
(c) Its cap is caps.json's study_per_issue, and the audit stage checks the
    per-issue cap on every real call as well as the day cap.
"""
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


P = _load("publish_study_mode", WHU / "publish.py")
SL = _load("spend_ledger_study_mode", ROOT / "backend" / "scripts" / "spend_ledger.py")
REASON = "SKIPPED — excluded from the frozen process for the study (protocol rev 27)"


@pytest.fixture
def study(tmp_path, monkeypatch):
    issues = tmp_path / "issues"
    d = issues / "WHU-P99-xq"
    (d / "draft").mkdir(parents=True)
    (d / "issue.json").write_text(json.dumps({"id": "WHU-P99", "slug": "xq", "title": "X",
                                              "study": True, "question": "Is X true?"}))
    (d / "draft" / "xq.html").write_text("<html><body><p>A sentence.</p></body></html>")
    other = issues / "WHU-P98-notstudy"
    other.mkdir()
    (other / "issue.json").write_text(json.dumps({"slug": "notstudy", "title": "N"}))
    monkeypatch.setattr(P, "CASES", issues)
    return d


# --- (a) registration --------------------------------------------------------

def test_a_study_issue_resolves_from_its_issue_json_and_not_from_ISSUES(study):
    assert "xq" not in P.ISSUES
    cfg = P.issue_cfg("xq")
    assert cfg["study"] is True and cfg["page"].endswith("WHU-P99-xq/draft/xq.html")
    assert "email_html" not in cfg and "url" not in cfg
    assert P.is_study("xq") and P.study_slugs() == ["xq"]
    assert not P.is_study("notstudy") and not P.is_study("melanoma")
    with pytest.raises(KeyError):
        P.issue_cfg("notstudy")                  # issue.json without study: true is not registered
    with pytest.raises(KeyError):
        P.issue_cfg("nosuchslug")


@pytest.mark.parametrize("cmd", ["cmd_publish", "cmd_update", "cmd_announce"])
def test_publish_update_and_announce_refuse_a_study_issue(study, monkeypatch, capsys, cmd):
    monkeypatch.setattr(P, "preflight", lambda *a, **k: pytest.fail("refused before any preflight"))
    args = types.SimpleNamespace(slug="xq", yes=True, waive=None, what="w", changed="c",
                                 source=None, subject=None, dry_run=False)
    assert getattr(P, cmd)(args) == 2
    assert "REFUSED" in capsys.readouterr().out


def test_bindings_reads_a_study_issues_page(study, monkeypatch):
    import bindings as B                         # the audit stage reads the page through this
    monkeypatch.setattr(B, "_publish", lambda: P)
    assert "A sentence." in B._page_html("xq")


# --- (b) the preflight -------------------------------------------------------

class _Stub(types.ModuleType):
    def __getattr__(self, name):
        return lambda *a, **k: []


def test_the_study_preflight_skips_the_four_and_never_reaches_the_live_site(study, monkeypatch):
    # Every sibling module is replaced by a stub returning no rows, so this test
    # isolates what publish.preflight itself does in study mode.
    for name, val in list(vars(P).items()):
        f = getattr(val, "__file__", "") or ""
        if isinstance(val, types.ModuleType) and f.startswith(str(ROOT / "backend" / "scripts")):
            monkeypatch.setattr(P, name, _Stub(name))
    monkeypatch.setattr(P, "spend", types.SimpleNamespace(cap_for=lambda s: 50.0, spent=lambda issue=None: 0.0))
    monkeypatch.setattr(P, "gate_report", lambda page: (P.OK, "gate stub"))
    monkeypatch.setattr(P, "queued_jobs_rows", lambda: [])
    monkeypatch.setattr(P, "live_body", lambda *a, **k: pytest.fail("the live site was fetched"))
    monkeypatch.setattr(P, "outside_review", lambda *a, **k: pytest.fail("outside review was run"))
    rows = P.preflight("xq", for_email=False)
    by = {l: (s, d) for l, s, d in rows}
    for label in ("outside review", "adjudication verification", "operator acceptance", "publication"):
        assert by[label][0] == P.OK and by[label][1].startswith(REASON), label
    assert by["page file"][0] == P.OK and by["page gate"] == (P.OK, "gate stub")
    assert by["spend on this issue"][0] == P.OK and "$50 cap" in by["spend on this issue"][1]
    for l in by:
        assert not l.startswith(("email", "html/text", "live page", "masthead", "page dateline",
                                 "correction recorded", "softened")), l


def test_a_study_issue_with_no_draft_page_is_blocked_on_the_page_file(study):
    (study / "draft" / "xq.html").unlink()
    rows = P.preflight("xq", for_email=False)
    assert rows == [("page file", P.BAD, "missing: %s" % (study / "draft" / "xq.html"))]


# --- (c) the cap --------------------------------------------------------------

@pytest.fixture
def ledger(tmp_path, monkeypatch, study):
    monkeypatch.setattr(SL, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(SL, "CAPS", tmp_path / "caps.json")
    monkeypatch.setattr(SL, "ISSUES_DIR", study.parent)
    (tmp_path / "caps.json").write_text(json.dumps({"default_per_issue": 40, "study_per_issue": 50,
                                                    "default_per_day": 1000, "per_issue": {}}))
    return tmp_path


def _spent(ledger, issue, usd):
    with open(ledger / "ledger.jsonl", "a") as f:
        f.write(json.dumps({"at": "2026-10-01T00:00:00+00:00", "script": "t", "issue": issue,
                            "usd": usd}) + "\n")


def test_a_study_issue_is_capped_at_the_study_cap(ledger):
    assert SL.cap_for("xq") == 50 and SL.cap_for("notstudy") == 40 and SL.cap_for("melanoma") == 40
    _spent(ledger, "xq", 45.0)
    SL.check_cap("xq", 4.0)                      # $49 is inside $50 (it would not be inside $40)
    with pytest.raises(SL.OverIssueCap):
        SL.check_cap("xq", 6.0)


def test_an_explicit_per_issue_entry_still_wins(ledger):
    caps = json.loads((ledger / "caps.json").read_text())
    caps["per_issue"] = {"xq": 10}
    (ledger / "caps.json").write_text(json.dumps(caps))
    assert SL.cap_for("xq") == 10


def test_the_audit_stage_checks_the_issue_cap_on_every_real_call(ledger, monkeypatch):
    A = _load("audit_stage_study_mode", WHU / "audit_stage.py")
    monkeypatch.setattr(A, "S", SL)
    _spent(ledger, "xq", 49.99)
    created = []

    class Raw:
        class messages:
            @staticmethod
            def count_tokens(**k):
                return types.SimpleNamespace(input_tokens=1000)

            @staticmethod
            def create(**k):
                created.append(k)

    call = A.Caller.__new__(A.Caller)
    call.cap, call.issue, call.calls = 100.0, "xq", []
    call._ask, call._day_cap, call._start = None, None, 0.0
    call._raw = call._client = Raw
    with pytest.raises(SL.OverIssueCap):
        call("prompt", 1000, "read")
    assert created == []


def test_the_spend_report_shows_a_study_issues_cap(ledger):
    # it printed "of $40 cap" for a study issue (WHU-S03, 2026-10-22)
    _spent(ledger, "xq", 10.0)
    _spent(ledger, "notstudy", 10.0)
    out = SL.report()
    line = {l.split()[0]: l for l in out.splitlines() if l.startswith("    ") and "cap" in l}
    assert "of $50 cap  (20%)" in line["xq"]
    assert "of $40 cap  (25%)" in line["notstudy"]
    assert "of $50 cap" in SL.report("xq")
