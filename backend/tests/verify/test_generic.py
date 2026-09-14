"""The generic-URL adapter: a page answers for itself, and the record says so.
Replayed from fixtures recorded 2026-09-14."""
import os, sys
from pathlib import Path
BACKEND = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(BACKEND))
os.environ.setdefault("VERIFY_CACHE_DIR", str(Path(__file__).parent / "fixtures" / "http"))
from verify import http  # noqa: E402
http.CACHE_DIR = Path(os.environ["VERIFY_CACHE_DIR"])
from verify import generic  # noqa: E402
from verify.bind import bind_heading, bind_all  # noqa: E402
from verify.status import check  # noqa: E402
from verify.types import Exists  # noqa: E402


def test_an_agency_page_is_fetched_and_bound_by_its_title():
    ident = generic.identify("https://www.ncbi.nlm.nih.gov/books/NBK25344/")
    assert ident.registry == "generic"
    res = generic.resolve(ident)
    assert res.exists == Exists.EXISTS and res.registry == "generic_fetch"
    doc = generic.fetch(res)
    assert doc and doc.route == "generic_fetch_html" and len(doc.text) > 1500
    assert bind_heading("Immunization Safety Review: Vaccines and Autism — Institute of Medicine", res).ok


def test_a_dead_url_is_nonexistent_not_unverifiable():
    res = generic.resolve(generic.identify("https://www.fda.gov/vaccines-blood-biologics/vaccines/mmr-ii"))
    assert res.exists == Exists.NONEXISTENT and res.registry == "generic_fetch"


def test_generic_has_no_status_registry_and_says_so():
    st = check(generic.identify("https://www.ncbi.nlm.nih.gov/books/NBK25344/"))
    assert st.verdict == "no_registry" and st.registry == "generic_fetch"


def test_registry_and_generic_are_distinguishable_on_the_record():
    from verify import literature
    assert literature.identify("https://doi.org/10.1056/NEJMoa021134").registry == "literature"
    assert generic.identify("https://www.cdc.gov/mmwr/preview/mmwrhtml/rr6204a1.htm").registry == "generic"
    assert generic.identify("not a url") is None
