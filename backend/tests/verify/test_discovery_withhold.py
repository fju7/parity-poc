"""S4 -> WITHHOLD: source discovery never writes an identifier the model produced.

Three things hold it: the prompts carry no identifier slot and name no
identifier system; _resolve_proposal discards any identifier-shaped field the
model returns for a literature source and takes the identifier only from
verify.search; a proposal the registries cannot resolve is marked UNRESOLVED
with the near-misses, and collect_sources refuses to load it.
"""
from __future__ import annotations

import importlib.util
import os
import sys

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BACKEND)

from verify.extract import extract, AssertionClass as A  # noqa: E402
from verify.policy import POLICY, Tier  # noqa: E402
from verify.types import Identifier, Provenance  # noqa: E402
import verify.search as vs  # noqa: E402


def _load_discovery():
    spec = importlib.util.spec_from_file_location("discover", os.path.join(BACKEND, "scripts", "signal", "00_discover_sources.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def test_policy_entry_is_withhold_and_wired():
    p = POLICY["scripts.signal.00_discover_sources::discover_sources"]
    assert p.tiers[A.IDENTIFIER] is Tier.WITHHOLD and p.wired


def test_prompts_carry_no_identifier_slot_and_name_no_identifier_system():
    d = _load_discovery()
    texts = [d.SYSTEM_PROMPT] + list(d.BATCH_PROMPTS.values())
    joined = "\n".join(texts)
    assert "doi.org" not in joined and "clinicaltrials.gov" not in joined.lower()
    assert "DOI" not in joined and "PMID" not in joined          # naming the thing puts it in context
    assert not extract(A.IDENTIFIER, joined), [c.text for c in extract(A.IDENTIFIER, joined)]
    assert '"citation"' not in joined


def test_literature_proposal_takes_its_identifier_only_from_the_registry(monkeypatch):
    d = _load_discovery()
    found = vs.Found(Identifier("doi", "10.1001/jama.2015.3077", "10.1001/jama.2015.3077", Provenance.SEARCHED),
                     "europepmc", "Autism occurrence by MMR vaccine status among US children with older siblings",
                     "https://doi.org/10.1001/jama.2015.3077", {"autism", "mmr", "siblings"}, 1.0, 2015, "Jain", {}, "t")
    monkeypatch.setattr(vs, "search", lambda *a, **k: found)
    proposal = {"slug": "jain-2015", "title": "Autism occurrence by MMR vaccine status among US children with older siblings",
                "first_author": "Jain", "year": 2015, "source_type": "observational",
                # what a model used to be able to smuggle in:
                "url": "https://doi.org/10.1001/jama.2015.1534", "doi": "10.1001/jama.2015.1534", "citation": "Jain A. JAMA 2015;313:1534"}
    out = d._resolve_proposal(proposal)
    assert out["identifier"] == "doi:10.1001/jama.2015.3077"           # the registry's, not the model's
    assert out["url"] == "https://doi.org/10.1001/jama.2015.3077"
    assert "1534" not in str(out) and "citation" not in out
    assert out["resolution"]["provenance"] == "SEARCHED"


def test_unresolvable_proposal_is_marked_not_guessed(monkeypatch):
    d = _load_discovery()
    monkeypatch.setattr(vs, "search", lambda *a, **k: vs.Unresolved("A completely invented trial", "no registry title matched", [("crossref", "something else")], "t"))
    out = d._resolve_proposal({"slug": "x", "title": "A completely invented trial", "source_type": "rct", "url": "https://doi.org/10.9999/fake"})
    assert "identifier" not in out and out["url"] is None
    assert out["unresolved"]["reason"].startswith("no registry title") and out["fetch_strategy"] == "unresolved"


def test_search_refuses_a_title_with_nothing_to_search_on():
    r = vs.search("MMR study")
    assert isinstance(r, vs.Unresolved)


def test_collect_sources_never_loads_an_unresolved_proposal():
    src = open(os.path.join(BACKEND, "scripts", "signal", "collect_sources.py"), encoding="utf-8").read()
    assert 'source.get("unresolved") or not source.get("url")' in src
