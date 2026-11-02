"""The check pilot's fresh-set draw (study/whu-reliability/check_pilot/fresh_draw.py), offline.

Europe PMC is stood in for by a fake that admits every candidate; IPCC statements are not fetched (the IPCC test
reads the frame's own rows through round 1's code path only where noted)."""
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(ROOT / "study" / "whu-reliability" / "check_pilot"))
import fresh_draw as D  # noqa: E402

COMMIT = "420f0d654bd1806e7c8f1db28aaceeb179e1089a"


def open_licence(url, **_kw):
    if "search?" in url:
        return SimpleNamespace(json=lambda: {"resultList": {"result": [{"license": "cc by", "pmcid": "PMC1"}]}})
    return SimpleNamespace(status_code=200, headers={"content-type": "application/xml"}, close=lambda: None)


def test_two_draws_per_frame_none_used_before_and_round1_globals_restored():
    before = (D.R.PLAN, D.R.EXTRA, D.R.random)
    for frame in ("cochrane", "campbell"):
        res = D.draw(frame, COMMIT, None, get=open_licence, pause=0)
        assert len(res["drawn"]) == 2 and res["round"] == "check-fresh-set"
        used = D.extend(before[1])["used_entries"][frame]
        assert not any(d.get("doi") in used for d in res["drawn"])
        assert all(d["result"] != "drawn" or d["k"] for d in res["log"])
    assert (D.R.PLAN, D.R.EXTRA, D.R.random) == before


def test_the_shuffle_is_the_labelled_seed_not_round_ones():
    fr = json.loads((D.STUDY / "frames" / "cochrane.json").read_text())
    order = sorted(e["k"] for e in fr["eligible"])
    seed = int(COMMIT, 16)
    mine, round1 = order[:], order[:]
    random.Random("%d/check-fresh-set" % seed).shuffle(mine)
    random.Random(seed).shuffle(round1)
    res = D.draw("cochrane", COMMIT, None, get=open_licence, pause=0)
    assert [r["k"] for r in res["log"]] == mine[:len(res["log"])] and mine != round1
    assert res["seed_label"] == "%d/check-fresh-set" % seed


def test_round1s_draws_are_used_before_and_its_questions_are_duplicates():
    ext = D.extend(D.R.EXTRA)
    assert ext["used_entries"]["cochrane"]["10.1002/14651858.CD012925.pub2"] == "WHU-Q1-01"
    assert ext["used_entries"]["ipcc"]["AR6-WGIII-C.11.4"] == "WHU-Q1-04"
    assert "10.1002/14651858.CD016194" in ext["used_entries"]["cochrane"]          # the study's, kept
    assert "WHU-Q1-01 (digital tracking, decision support and client reminders in primary care)" not in D.R.EXTRA[
        "patterns"]                                                               # round 1's table untouched
    saved = D.R.EXTRA
    D.R.EXTRA = ext
    try:
        assert D.R.duplicates("Mefloquine for preventing malaria in travellers")
        assert D.R.duplicates("Interventions for improving educational outcomes of children with disabilities")
        assert D.R.duplicates("Direct air capture and other carbon dioxide removal methods are needed for net zero.")
        assert not D.R.duplicates("Zinc supplementation for the common cold in children")
    finally:
        D.R.EXTRA = saved


def test_a_redraw_repeats_the_shuffle_logs_the_rejection_and_takes_the_next():
    first = D.draw("campbell", COMMIT, None, get=open_licence, pause=0)
    again = D.draw("campbell", COMMIT, None, get=open_licence, pause=0, redraw=1)
    assert [r["k"] for r in again["log"]][:len(first["log"])] == [r["k"] for r in first["log"]]
    rejected = [r for r in again["log"] if r["result"] == "ineligible" and "closer reading" in r.get("why", "")]
    assert len(rejected) == 1 and "cl2.1419" not in [d.get("doi") for d in again["drawn"]]
    assert len(again["drawn"]) == 2 and again["redraw"]["n"] == 1
    assert "10.1002/cl2.1419" not in D.extend(D.R.EXTRA)["used_entries"]["campbell"]     # only on a redraw


def test_import_pages_stores_each_saved_page_under_its_url_unchanged(tmp_path):
    import gzip
    page = b"<html><p>A.1 It is unequivocal that human influence has warmed the planet. {2.1}</p></html>"
    for name in D.SAVED_PAGES:
        (tmp_path / name).write_bytes(page)
    assert D.import_pages(tmp_path) == 0
    for url in D.SAVED_PAGES.values():
        assert gzip.decompress((tmp_path / (D.F.sha(url)[:32] + ".gz")).read_bytes()) == page
    assert set(D.SAVED_PAGES.values()) == {u for _w, _t, _y, u in D.F.IPCC_REPORTS}
    (tmp_path / "ipcc-ar6-syr-spm.html").unlink()
    assert D.import_pages(tmp_path) == 1
