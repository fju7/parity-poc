"""The REAL preflight runs on a synthetic study issue (2026-10-20).

Found by the WHU-P02 practice run: publish.slug_for() searched only ISSUES, so a
study page resolved to slug None; registry_figures.case_dir(None) raised
SystemExit, which publish.registry_overturns' `except Exception` does not
catch, and the preflight died. slug_for now resolves study issues through
issue_cfg, and the registry modules' case_dir raises NoCaseDir, an ordinary
exception.

Every sibling module resolves its case directory from ROOT/issues by its own
constant, several are loaded lazily or under other names, so the synthetic
issue is created where they look -- issues/WHU-P9Z-pytest-synthetic-study --
and removed whatever happens. No network: sockets are refused.
"""
import importlib.util
import json
import shutil
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
SLUG = "pytest-synthetic-study"
CASE = ROOT / "issues" / ("WHU-P9Z-%s" % SLUG)
PAGE = "<html><body><article>%s<p>In 2024 a trial of 120 adults found a 2 kg loss.</p></article></body></html>" % "".join(
    "<p>Paragraph %d of a synthetic study answer says something plain about diets and weight, with no "
    "figure in it at all, so that nothing here needs a source to settle it.</p>" % i for i in range(12))


@pytest.fixture
def synthetic(monkeypatch):
    assert not CASE.exists(), "a leftover synthetic issue: %s" % CASE
    try:
        (CASE / "draft").mkdir(parents=True)
        (CASE / "issue.json").write_text(json.dumps({"id": "WHU-P9Z", "slug": SLUG, "title": "Q?",
                                                     "study": True}))
        (CASE / "draft" / ("%s.html" % SLUG)).write_text(PAGE)
        (CASE / "sources.json").write_text(json.dumps({"sources": []}))
        (CASE / "premise.json").write_text(json.dumps({"direction": {"value": "corrects"}}))

        def refused(*a, **k):
            raise OSError("network refused in this test")
        monkeypatch.setattr(socket, "create_connection", refused)
        spec = importlib.util.spec_from_file_location("publish_study_preflight_t", WHU / "publish.py")
        P = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(P)
        yield P
    finally:
        shutil.rmtree(CASE, ignore_errors=True)


def test_slug_for_resolves_a_study_page(synthetic):
    P = synthetic
    assert P.slug_for(CASE / "draft" / ("%s.html" % SLUG)) == SLUG
    assert P.slug_for(P.ROOT / P.ISSUES["melanoma"]["page"]) == "melanoma"


def test_the_registry_case_lookup_raises_an_ordinary_exception():
    spec = importlib.util.spec_from_file_location("registry_figures_t", WHU / "registry_figures.py")
    RF = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(RF)
    with pytest.raises(Exception) as e:
        RF.case_dir(None)
    assert isinstance(e.value, RF.NoCaseDir) and not isinstance(e.value, SystemExit)


def test_the_real_preflight_runs_on_a_synthetic_study_issue(synthetic):
    P = synthetic
    rows = P.preflight(SLUG, for_email=False)            # must not raise
    by = {l: (s, d) for l, s, d in rows}
    for label in ("outside review", "adjudication verification", "operator acceptance", "publication"):
        assert by[label][1].startswith("SKIPPED — excluded from the frozen process"), label
    assert "registry figures" in by and by["registry figures"][0] == P.OK
    assert by["contrarianism guard"] == (P.OK, "SKIPPED — the study's questions are chosen by the "
                                               "protocol, not by WHU (protocol rev 27)")
    assert by["the correction history is checked"] == (
        P.OK, "SKIPPED — a study answer is never published, so it has no correction history "
              "(protocol rev 27)")
    assert not any(l.startswith(("email", "live page", "masthead")) for l in by)


def test_the_canary_row_is_a_normal_check_on_a_study_issue(synthetic, monkeypatch):
    """canary.py runs on study issues (RUN.md step 2c); its preflight row is the
    ordinary check, not SKIPPED (protocol rev 38, undoing 6c4e575)."""
    P = synthetic
    ran = []
    monkeypatch.setattr(P.canary, "preflight_rows",
                        lambda slug: ran.append(slug) or [("checks can read the documents", P.OK, "1 of 1")])
    by = {l: (s, d) for l, s, d in P.preflight(SLUG, for_email=False)}
    assert ran == [SLUG]
    assert by["checks can read the documents"] == (P.OK, "1 of 1")
    assert not hasattr(P, "CANARY_STUDY_REASON")


def test_the_study_preflight_checks_the_frozen_files(synthetic):
    P = synthetic
    by = {l: (s, d) for l, s, d in P.preflight(SLUG, for_email=False)}
    assert by["frozen files unchanged"][0] == P.OK and "frozen.py" in by["frozen files unchanged"][1]
