"""Check-an-answer pilot v2 (study/whu-reliability/check_pilot/pipeline_v2.py), offline.
Design: docs/whu-check-an-answer-pilot.md §9. Every network step is replaced; no model call."""
import hashlib
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1].parent
FIX = Path(__file__).resolve().parent / "fixtures" / "whu_check"
sys.path.insert(0, str(ROOT / "study" / "whu-reliability" / "check_pilot"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline_v2 as V2  # noqa: E402
import test_whu_check_pilot as T  # noqa: E402

SOURCE = (FIX / "source_PMC10771715.txt").read_text(encoding="utf-8")


class Net:
    """Recorded network: records every address fetched."""

    def __init__(self, robots=True, page="", crossref=None, licence="cc by"):
        self.fetched, self.robots_asked, self._robots, self._page = [], [], robots, page
        self._crossref, self._licence = crossref, licence

    def table(self):
        return {"robots": self.robots, "page": self.page, "crossref": self.crossref, "licence": self.licence,
                "retrieve": self.retrieve, "open_copy": self.open_copy}

    def robots(self, url):
        self.robots_asked.append(url)
        return (self._robots, "robots.txt %s it" % ("allows" if self._robots else "disallows"))

    def page(self, url):
        self.fetched.append(url)
        return self._page

    def crossref(self, title):
        return (self._crossref, "Crossref title match (recorded)") if self._crossref else (None, "no match")

    def licence(self, ids):
        return {"licence": self._licence, "by": "recorded"}

    def _write(self, url, work, how):
        self.fetched.append(url)
        sid = "S" + hashlib.sha256(url.encode()).hexdigest()[:12]
        (work / "sources").mkdir(parents=True, exist_ok=True)
        (work / "sources" / (sid + ".txt")).write_text(SOURCE, encoding="utf-8")
        return {"url": url, "source_id": sid, "extent": "full text", "extent_why": how, "abstract_only": False}

    def retrieve(self, url, work):
        return self._write(url, work, "recorded (a)")

    def open_copy(self, url, work):
        return self._write(url, work, "recorded (c)")


def test_the_trailing_full_is_trimmed_in_the_pilots_copy_only():
    import find_access as FA
    u = "https://www.frontiersin.org/journals/psychiatry/articles/10.3389/fpsyt.2019.00552/full"
    assert FA.ids_from_url(u)["doi"] == "10.3389/fpsyt.2019.00552/full"      # the study's helper, unchanged
    assert V2.ids_v2(u)["doi"] == "10.3389/fpsyt.2019.00552"


def test_barred_hosts_are_never_fetched(tmp_path):
    for u, who in (("https://www.sciencedirect.com/science/article/pii/S0140673623012310", "Elsevier"),
                   ("https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(23)01231-X/fulltext", "Elsevier"),
                   ("https://www.nccn.org/guidelines/x", "NCCN")):
        n = Net()
        row = V2.source_v2(u, "A title of the cited work here", tmp_path, n.table())
        assert row["extent"] == "unreachable" and who in row["extent_why"]
        assert n.fetched == [] and n.robots_asked == []


def test_an_elsevier_doi_is_barred_wherever_it_is_cited(tmp_path):
    n = Net()
    row = V2.source_v2("https://doi.org/10.1016/j.adolescence.2018.05.011", None, tmp_path, n.table())
    assert "Elsevier" in row["extent_why"] and n.fetched == []


def test_sage_and_wiley_without_cc_are_barred_and_with_cc_read_only_from_an_open_copy(tmp_path):
    u = "https://journals.sagepub.com/doi/10.1177/1473225420938151"
    n = Net(licence=None)
    row = V2.source_v2(u, None, tmp_path, n.table())
    assert "SAGE" in row["extent_why"] and n.fetched == []
    n = Net(licence="cc by")
    row = V2.source_v2(u, None, tmp_path, n.table())
    assert row["extent"] == "full text" and row["extent_why"] == "recorded (c)"
    w = "https://www.cochranelibrary.com/cdsr/doi/10.1002/14651858.CD009593.pub3/full"
    n = Net(licence=None)
    row = V2.source_v2(w, None, tmp_path, n.table())
    assert "Wiley" in row["extent_why"] and n.fetched == []


def test_a_doi_is_read_from_the_landing_page_meta(tmp_path):
    page = '<html><head><meta name="citation_doi" content="10.2196/29842"></head></html>'
    n = Net(page=page)
    row = V2.source_v2("https://www.jmir.org/2022/4/e29842", None, tmp_path, n.table())
    assert row["ids"] == {"doi": "10.2196/29842"} and "meta" in row["ids_how"]
    assert V2.doi_from_meta('<meta content="https://doi.org/10.1234/abc" name="dc.identifier">') == "10.1234/abc"


def test_a_crossref_title_lookup_when_the_page_has_no_doi(tmp_path):
    n = Net(page="<html>no meta</html>", crossref="10.1007/s00787-021-01884-6")
    row = V2.source_v2("https://example.org/paper", "The effects of psychological treatments of depression", tmp_path, n.table())
    assert row["ids"]["doi"] == "10.1007/s00787-021-01884-6" and row["licence"] == "cc by"


def test_a_journal_work_without_an_open_licence_stays_couldnt_check(tmp_path):
    n = Net(page="<html></html>", crossref="10.9999/x", licence=None)
    row = V2.source_v2("https://example.org/paper", "Some paper title words here", tmp_path, n.table())
    assert row["why_kind"] == "no open licence" and n.fetched == ["https://example.org/paper"]  # the landing page only


def test_a_web_page_is_fetched_where_robots_allows_and_not_where_it_disallows(tmp_path):
    u = "https://uea.ac.uk/about/news/article/technology-assisted-therapy-example"
    n = Net(page="<html></html>")
    row = V2.source_v2(u, None, tmp_path, n.table())
    assert row["extent"] == "full text" and row.get("kind") == "web page"
    n = Net(robots=False)
    row = V2.source_v2(u, None, tmp_path, n.table())
    assert row["why_kind"] == "robots.txt disallows" and n.fetched == []


def test_one_full_v2_check_on_the_recorded_answer(tmp_path):
    text = (FIX / "answer_claude_sources.md").read_text(encoding="utf-8")
    n = Net(page="<html></html>")
    prep = V2.prepare(text, tmp_path, count=T.count, net=n.table())
    c = T.client()
    res = V2.judge(prep["planned"], c)
    labels = sorted(r["label"] for r in res)
    # v1 left the news release COULDN'T CHECK; v2 reads it as a web page (robots allows)
    assert labels.count(V2.COULDNT) == 0 and labels.count(V2.NO_SOURCE) == 1
    assert prep["version"] == 2


def test_titles_come_from_the_answers_own_links():
    t = V2.titles_from("1. [A comparison of the effectiveness](https://a.org/x) 2. [https://b.org](https://b.org)")
    assert t == {"https://a.org/x": "A comparison of the effectiveness"}


def test_the_v2_sample_is_v1s_complement():
    spec = importlib.util.spec_from_file_location("run_pilot_v2_t", ROOT / "study" / "whu-reliability" / "check_pilot" / "run_pilot_v2.py")
    R2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(R2)
    v1, v2 = set(R2.V1_DRAW()), set(R2.draw())
    assert len(v2) == 8 and not (v1 & v2)
    assert len(v1 | v2) == 16
