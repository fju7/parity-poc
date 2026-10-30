"""Check-an-answer pilot v4 (study/whu-reliability/check_pilot/pipeline_v4.py), offline.

v4 = v3 with lean WHU's passage retrieval: the judge reads the top-k passages for the claim (plus a
passage per missing key term), never the whole source. Every network step is v3's recorded reply;
the judge is the v1 tests' recorded client. No model call."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1].parent
sys.path.insert(0, str(ROOT / "study" / "whu-reliability" / "check_pilot"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_v3 as P3  # noqa: E402
import pipeline_v4 as P4  # noqa: E402
import test_whu_check_pilot as T  # noqa: E402
import test_whu_check_pilot_v3 as T3  # noqa: E402

PMC = "https://pmc.ncbi.nlm.nih.gov/articles/PMC10771715/"
UEA = "https://uea.ac.uk/about/news/article/technology-assisted-therapy-example"


def _answer():
    return (T3.FIX / "answer_claude_sources.md").read_text(encoding="utf-8")


def _net():
    return T3.Net({PMC: T3.reply(), UEA: T3.reply()}).table()


def test_v4_judges_passages_not_the_whole_source_and_logs_retrieval(tmp_path):
    p3 = P3.prepare(_answer(), tmp_path / "v3", count=T.count, net=_net())
    p4 = P4.prepare(_answer(), tmp_path / "v4", count=T.count, net=_net())
    judged3 = {p["idx"]: p for p in p3["planned"] if p["label"] is None}
    judged4 = {p["idx"]: p for p in p4["planned"] if p["label"] is None}
    assert judged4 and p4["version"] == 4 and p4["retrieval"]
    for i, p in judged4.items():
        for d in p["docs"]:
            # the fixture is a 5,128-character excerpt; on it six passages are most of it
            assert d["passages"] and len(d["text"]) < len(T3.SOURCE)
        if i in judged3:
            assert p["n_in"] < judged3[i]["n_in"]                 # fewer tokens than v3 for the same claim
    assert p4["worst_usd"] < p3["worst_usd"]


def test_a_full_v4_check_carries_passages_located_in_the_full_text(tmp_path):
    out = P4.check(_answer(), tmp_path, T.client(), T.count, net=_net())
    assert out["summary"].startswith("4 of 4 claims checked")
    for r in out["results"]:
        if r["label"] in (P4.BACKED, P4.NOT_BACKED):
            assert r["passage"]["words"] < 60 and r["passage"]["link"]
        if r["label"] == P4.COULDNT:
            assert r["reason_kind"] in P3.REASONS + (P4.R_NO_PASSAGE,)


def test_nothing_above_threshold_is_couldnt_check_never_the_whole_source():
    sent, rec = P4.passages_for(T3.SOURCE, "Zebra quokka marmalade.")
    assert sent == "" and rec["below_threshold"]


def test_a_missing_key_term_is_topped_up_so_the_delivery_check_holds():
    text = ("\n\n".join("Paragraph %d on cognitive behavioural therapy outcomes in adolescents." % i for i in range(60))
            + "\n\nThe remission rate was 41.7% at follow-up in the Lindqvist cohort.")
    claim = "Cognitive behavioural therapy outcomes improved, with remission of 41.7% in the Lindqvist cohort."
    sent, rec = P4.passages_for(text, claim, k=1)
    assert "41.7%" in sent and not P4.J.delivery_problems(text, sent, claim, [])
    assert len(sent) < len(text) / 4


def test_the_preview_stays_on_v2():
    src = (ROOT / "backend" / "routers" / "whu_check.py").read_text(encoding="utf-8")
    assert "PIPELINE_VERSION = 2" in src
