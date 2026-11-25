"""Advisor's rulings after orchestrator trial 1 attempt 24's fresh run (2026-11-25, P094).

Attempt 24 stopped at `draft` on the source-list check, "[6] more than one year (2010, 2018, 2017)": S006 (UNESCO
2017, doi 10.54675/mhhz2237) was confirmed by Crossref, whose record names an organisational author "UNESCO. Assistant
Director-General for Education, 2010-2018 (Qian Tang)". registries.epmc_shaped_from_crossref joined the names with
", " and source_entries.record_from_fallback split them again at every comma.

  (1) author lists come from Crossref's structured fields (given/family for persons, name for organisations), never
      joined and re-split; an organisational name's trailing tenure qualifier ", YYYY-YYYY (...)" is dropped from the
      shown name and the full registry string kept; the one-year check stays strict;
  (3) a standing check's findings stop the run with their own wording, not the ownership breach's.

The fixture is Crossref's work record for 10.54675/mhhz2237, fetched 2026-11-25 (Crossref metadata is CC0).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
FIX = ROOT / "backend" / "tests" / "fixtures" / "whu_orch_crossref" / "work_10.54675_mhhz2237.json"

import registries as RG          # noqa: E402
import source_entries as SE      # noqa: E402

FULL = "UNESCO. Assistant Director-General for Education, 2010-2018 (Qian Tang)"
SHOWN = "UNESCO. Assistant Director-General for Education"
TITLE = "A Guide for ensuring inclusion and equity in education"


def _s006_item() -> dict:
    return json.loads(FIX.read_text(encoding="utf-8"))["message"]


def _src(record: dict) -> dict:
    return {"id": "S006", "title": TITLE, "year": 2017, "registry_record": record}


def test_the_recorded_s006_crossref_response_is_what_attempt_24_met():
    it = _s006_item()
    assert it["DOI"].lower() == "10.54675/mhhz2237" and it["title"] == [TITLE]
    assert [a.get("name") for a in it["author"]] == [FULL, "UNESCO"]
    assert not any(a.get("family") for a in it["author"])


def test_s006_authors_come_from_the_structured_fields_with_the_tenure_dropped():
    shown, full = RG.crossref_authors(_s006_item())
    assert shown == [SHOWN, "UNESCO"]
    assert full == [FULL, "UNESCO"]                       # the registry's own strings, kept
    rec = RG.epmc_shaped_from_crossref(_s006_item())
    assert rec["authors"] == [SHOWN, "UNESCO"] and rec["authors_registry"] == [FULL, "UNESCO"]


def test_s006_entry_has_one_year_and_passes_the_strict_check():
    rec = SE.record_from_fallback(RG.epmc_shaped_from_crossref(_s006_item()), "crossref")
    assert rec["authors"] == [SHOWN, "UNESCO"]
    assert rec["authors_registry"] == [FULL, "UNESCO"]
    assert rec["year"] == 2017 and rec["title"] == TITLE
    src = _src(rec)
    text = SE.entry_text(src)
    assert text == "%s, UNESCO. %s. 2017." % (SHOWN, TITLE)
    assert SE.problems(src, text) == []
    html = SE.entry_html(1, src)
    assert SE.page_problems([src], '<div class="sources">%s</div>' % html) == []


def test_the_old_join_and_split_reproduces_attempt_24s_stop():
    """What attempt 24 did: the joined authorString split again at every comma."""
    rec = RG.epmc_shaped_from_crossref(_s006_item())
    old = dict(rec, authorString=", ".join(RG.crossref_authors(_s006_item())[1]))
    old.pop("authors")
    got = SE.record_from_fallback(old, "crossref")
    assert got["authors"] == ["UNESCO. Assistant Director-General for Education", "2010-2018 (Qian Tang)", "UNESCO"]
    src = _src(got)
    assert SE.problems(src, SE.entry_text(src)) == ["more than one year (2010, 2018, 2017)"]


def test_a_person_with_a_comma_in_the_name_stays_one_author():
    it = {"title": ["A trial of something"], "container-title": ["J Things"], "DOI": "10.1/x",
          "issued": {"date-parts": [[2020]]},
          "author": [{"family": "King, Jr.", "given": "Martin Luther", "sequence": "first"},
                     {"family": "van der Linden", "given": "Sander", "sequence": "additional"},
                     {"family": "Smith", "given": "J.-P.", "sequence": "additional"}]}
    shown, full = RG.crossref_authors(it)
    assert shown == ["King, Jr. ML", "van der Linden S", "Smith JP"]
    assert full == ["King, Jr., Martin Luther", "van der Linden, Sander", "Smith, J.-P."]
    rec = SE.record_from_fallback(RG.epmc_shaped_from_crossref(it), "crossref")
    assert rec["authors"] == shown and len(rec["authors"]) == 3          # not split at "King," / "Jr."
    src = {"id": "S001", "title": "A trial of something", "registry_record": rec}
    text = SE.entry_text(src)
    assert text == "King, Jr. ML, van der Linden S, Smith JP. A trial of something. J Things. 2020."
    assert SE.problems(src, text) == []


@pytest.mark.parametrize("name, shown", [
    ("UNESCO. Assistant Director-General for Education, 2010-2018 (Qian Tang)",
     "UNESCO. Assistant Director-General for Education"),
    ("World Health Organization, 1998–2003 (G. H. Brundtland)", "World Health Organization"),
    ("Office of the Director, 2015- (Jane Doe)", "Office of the Director"),
    ("WHO Guideline Development Group", "WHO Guideline Development Group"),
    ("Report Committee, 2010 (draft)", "Report Committee, 2010 (draft)"),          # not ", YYYY-YYYY (...)"
    ("Commission (2010-2018) on Education", "Commission (2010-2018) on Education"),  # not trailing
])
def test_the_tenure_qualifier_is_dropped_only_in_its_trailing_form(name, shown):
    s, f = RG.crossref_authors({"author": [{"name": name}]})
    assert s == [shown] and f == [name]


def test_a_person_name_is_never_trimmed():
    s, _ = RG.crossref_authors({"author": [{"family": "Tang, 2010-2018 (Q)", "given": "Qian"}]})
    assert s == ["Tang, 2010-2018 (Q) Q"]


def test_the_one_year_check_stays_strict():
    """A year inside an author name still fails the entry: the check is not loosened, the name is shown cleanly."""
    rec = {"registry": "crossref", "authors": ["Group, 2010 (draft)"], "year": 2017, "title": TITLE,
           "container": None}
    src = _src(rec)
    assert SE.problems(src, SE.entry_text(src)) == ["more than one year (2010, 2017)"]


def test_the_crossref_record_still_confirms_s006_through_the_ported_rule():
    from orch import resolve as RV
    rec = RG.epmc_shaped_from_crossref(_s006_item())
    got = RV._checked(rec, TITLE, "UNESCO", 2017, registry="crossref")
    assert isinstance(got, RV.Found) and got.identifier.value.lower() == "10.54675/mhhz2237"
    assert got.extra["record"]["authors"] == [SHOWN, "UNESCO"]
    assert got.extra["record"]["authors_registry"] == [FULL, "UNESCO"]


def test_pubmed_summaries_keep_their_author_list():
    r = {"uid": "1", "title": "T.", "pubdate": "2020 Jan", "authors": [{"name": "Saran A"}, {"name": "White H"}],
         "articleids": [{"idtype": "doi", "value": "10.1/y"}], "fulljournalname": "J"}
    rec = RG.epmc_shaped_from_summary(r)
    assert rec["authors"] == ["Saran A", "White H"] and rec["authorString"] == "Saran A, White H"
    assert SE.record_from_fallback(rec, "pubmed")["authors"] == ["Saran A", "White H"]


def test_an_epmc_record_without_a_list_still_splits_its_author_string():
    rec = {"authorString": "Saran A, White H, Kuper H.", "pubYear": "2020", "title": "T", "journalTitle": "J"}
    assert SE.record_from_fallback(rec, "pubmed")["authors"] == ["Saran A", "White H", "Kuper H"]


# ---- (3) the stop wording -----------------------------------------------------------------------------------

def _ctx(tmp_path, monkeypatch):
    import orchestrator as O
    c = tmp_path / "case"
    (c / "orchestrator").mkdir(parents=True)
    (c / "issue.json").write_text("{}")
    ctx = O.Ctx.__new__(O.Ctx)
    ctx.slug, ctx.case, ctx.mode, ctx.root, ctx.lock, ctx.frozen, ctx.log = "orch-x", c, "trial", tmp_path, None, {}, []
    monkeypatch.setattr(O, "_study_log", lambda *a: None)
    return O, ctx


def test_a_standing_check_finding_stops_with_its_own_wording(tmp_path, monkeypatch):
    O, ctx = _ctx(tmp_path, monkeypatch)
    from orch import chain as CH, steps as ST
    finding = O.ENTRY_PREFIX + "[6] more than one year (2010, 2018, 2017)"
    monkeypatch.setattr(O, "_account_page", lambda ctx, step: [finding])
    monkeypatch.setitem(O.STEP_CODE, "quiet", lambda ctx, step: None)
    step = ST.Step("bind", "code", owns=("bindings.json",), code="quiet")
    with pytest.raises(O.RunStop) as e:
        O.run_step(ctx, step)
    msg = str(e.value)
    assert msg == "bind: %s: %s" % (O.CHECK_STOP, finding)
    assert CH.STOP not in msg and O.CHECK_STOP != CH.STOP


def test_an_ownership_breach_keeps_the_ownership_wording(tmp_path, monkeypatch):
    O, ctx = _ctx(tmp_path, monkeypatch)
    from orch import chain as CH, steps as ST
    monkeypatch.setattr(O, "_account_page", lambda ctx, step: [O.ENTRY_PREFIX + "[1] doubled punctuation"])
    monkeypatch.setitem(O.STEP_CODE, "rogue", lambda ctx, step: (ctx.case / "omissions.json").write_text("{}"))
    step = ST.Step("bind", "code", owns=("bindings.json",), code="rogue")
    with pytest.raises(O.RunStop) as e:
        O.run_step(ctx, step)
    assert CH.STOP in str(e.value) and "created omissions.json" in str(e.value)


def test_no_finding_no_stop(tmp_path, monkeypatch):
    O, ctx = _ctx(tmp_path, monkeypatch)
    from orch import steps as ST
    monkeypatch.setattr(O, "_account_page", lambda ctx, step: [])
    monkeypatch.setattr(O, "step_code_hash", lambda step: "h")
    monkeypatch.setitem(O.STEP_CODE, "quiet", lambda ctx, step: None)
    step = ST.Step("bind", "code", owns=("bindings.json",), code="quiet")
    assert O.run_step(ctx, step)["code_hash"] == "h"
