"""The publish gate on links to already-changed sources (ruling of 2026-09-14).

A claim whose SUPPORT was retracted (or corrected, superseded, amended)
before the freeze is UNSUPPORTED -- refused at publish, not published with a
warning. A claim whose SUBJECT is the retracted work stays publishable. So
the red marker only ever means "this changed after we froze it". Also the
link-role rule and its audit record: which rule fired and what matched.

Wakefield 1998 is the reference case, replayed from fixtures.
"""
import json
import os, sys
from pathlib import Path
BACKEND = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(BACKEND))
os.environ.setdefault("VERIFY_CACHE_DIR", str(Path(__file__).parent / "fixtures" / "http"))
from verify import http  # noqa: E402
http.CACHE_DIR = Path(os.environ["VERIFY_CACHE_DIR"])
from verify import literature  # noqa: E402
from verify.publish import gate_claim, link_role, REFUSING_STATUS_AT_PUBLISH  # noqa: E402

WAKE = "https://doi.org/10.1016/S0140-6736(97)11096-0"


def _wakefield_source():
    ident = literature.identify(WAKE)
    res = literature.resolve(ident)
    doc = literature.fetch(res)
    return {"id": "src-wake", "title": "Ileal-lymphoid-nodular hyperplasia, non-specific colitis, and pervasive developmental disorder in children",
            "url": WAKE, "survives": True, "_res": res, "_doc": doc,
            "status": {"verdict": "retracted", "events": [{"type": "retraction", "date": "2010-2-6"}]}, "registry_text": ""}


def test_subject_link_is_admissible_and_audited():
    src = _wakefield_source()
    claim = {"id": "c1", "claim_text": "The Wakefield et al. case series enrolled only 12 children.", "category": "x"}
    out = gate_claim(claim, [{"claim_id": "c1", "source_id": "src-wake"}], {"src-wake": src})
    ps = out["per_source"][0]
    assert ps["role"] == "subject" and ps["role_rule"] == {"matched": "Wakefield", "kind": "first_author"}
    assert out["support"] == "FIGURE_BOUND"
    assert any(b["kind"] == "STATUS_AT_PUBLISH" and b["ok"] for b in ps["bindings"])


def test_support_link_to_a_retracted_source_is_refused_at_publish():
    src = _wakefield_source()
    claim = {"id": "c2", "claim_text": "Measles virus persists in the gut tissue of children with autism.", "category": "x"}
    out = gate_claim(claim, [{"claim_id": "c2", "source_id": "src-wake"}], {"src-wake": src})
    ps = out["per_source"][0]
    assert ps["role"] == "support" and ps["role_rule"]["kind"] == "no_name_in_claim"
    assert out["support"] == "UNSUPPORTED"
    b = next(b for b in ps["bindings"] if b["kind"] == "STATUS_AT_PUBLISH")
    assert not b["ok"] and "retracted before publication" in b["reason"]


def test_every_alerting_status_refuses_a_support_link_and_the_set_is_the_status_checks():
    from verify.status import Status
    from verify.types import Identifier
    assert REFUSING_STATUS_AT_PUBLISH == {v for v in ("retracted", "withdrawn", "concern", "corrected", "superseded",
                                                      "trial_status_changed", "amended", "reissued")}
    assert all(Status(Identifier("doi", "x"), v).alerts for v in REFUSING_STATUS_AT_PUBLISH)


def test_title_word_rule_and_its_record():
    src = _wakefield_source()
    role, rule = link_role("The ileal-lymphoid-nodular hyperplasia paper described 12 children.", src)
    assert role == "subject" and rule["kind"] == "title_word" and rule["matched"] in ("lymphoid", "hyperplasia", "nodular", "developmental")


def test_erratum_precision_touched_untouched_and_unreadable():
    """An erratum corrects something inside a work that otherwise stands (2026-09-15)."""
    from verify.publish import erratum_check, _erratum_cache
    src = {"id": "src-e", "status": {"verdict": "corrected", "events": [{"type": "erratum in", "id": "26757477"}]}}
    _erratum_cache["src-e"] = [{"doi": "10.1001/jama.2015.17754", "pmid": "26757477", "title": "Incorrect Variable Description.",
                                "date": 2016, "text": "In the table, the hazard ratio 0.80 was mislabelled as 0.85.", "route": "test"}]
    assert not erratum_check(["0.8"], src)["ok"]              # touched
    assert erratum_check(["95727"], src)["ok"]                # untouched -> publish with marker
    _erratum_cache["src-e"] = [{"doi": "10.1001/jama.2015.17754", "pmid": "26757477", "title": "Incorrect Variable Description.",
                                "date": 2016, "text": None, "route": "unretrievable (publisher HTTP 403)"}]
    r = erratum_check(["95727"], src)
    assert not r["ok"] and "could not be read" in r["reason"]  # fail closed
    _erratum_cache.pop("src-e")


def test_a_claim_whose_only_figure_is_a_year_is_source_confirmed_not_figure_bound():
    """2026-09-15: 29 of 64 FIGURE_BOUND claims on the mmr record were bound on
    a year alone -- "the Wakefield 1998 study ..." -- because gate_claim
    counted the year as a figure and FIGURE then had nothing to check. The
    year is CHRONOLOGY's; a year-only claim is IDENTITY_ONLY. A claim that
    also states a figure is still FIGURE_BOUND on the figure."""
    src = _wakefield_source()
    year_only = {"id": "c3", "claim_text": "The Wakefield 1998 case series was published in The Lancet.", "category": "x"}
    out = gate_claim(year_only, [{"claim_id": "c3", "source_id": "src-wake"}], {"src-wake": src})
    assert out["figures"] == [] and out["years"] == ["1998"]
    assert out["support"] == "IDENTITY_ONLY", out["per_source"][0]["bindings"]
    assert not any(b["kind"] == "FIGURE" for b in out["per_source"][0]["bindings"])   # nothing to check, so no FIGURE binding
    assert any(b["kind"] == "CHRONOLOGY" and b["ok"] for b in out["per_source"][0]["bindings"])
    with_figure = {"id": "c4", "claim_text": "The Wakefield 1998 case series enrolled only 12 children.", "category": "x"}
    out2 = gate_claim(with_figure, [{"claim_id": "c4", "source_id": "src-wake"}], {"src-wake": src})
    assert out2["figures"] == ["12"] and out2["support"] == "FIGURE_BOUND"


def test_an_operator_withheld_claim_is_unsupported_with_the_reason_and_no_binding_runs(monkeypatch, tmp_path):
    """data/verify/withheld_claims.json is refuse-only: it can withhold a claim
    whose content the operator found absent from its source; nothing in it can
    admit one. The record carries who, when and what was checked."""
    from verify import publish
    reg = tmp_path / "withheld_claims.json"
    reg.write_text(json.dumps({"claims": {"c9": {"reason": "asserts a finding the study did not make: 'no dose-response'",
                                                   "checked_against": "the abstract", "withheld_by": "test", "withheld_on": "2026-09-15", "ruled_by": "the operator"}}}))
    monkeypatch.setattr(publish, "WITHHELD_CLAIMS", reg)
    src = _wakefield_source()
    out = gate_claim({"id": "c9", "claim_text": "The Wakefield 1998 case series enrolled only 12 children.", "category": "x"},
                     [{"claim_id": "c9", "source_id": "src-wake"}], {"src-wake": src})
    assert out["support"] == "UNSUPPORTED" and out["withheld_reason"].startswith("OPERATOR_WITHHELD: asserts a finding")
    assert out["operator_withheld"]["withheld_by"] == "test" and out["per_source"][0]["bindings"][0]["kind"] == "OPERATOR_WITHHELD"
    assert not any(b["kind"] in ("FIGURE", "CHRONOLOGY", "SPAN") for b in out["per_source"][0]["bindings"])   # nothing else ran
    # an unlisted claim is untouched: the register cannot admit, only withhold
    out2 = gate_claim({"id": "c10", "claim_text": "The Wakefield 1998 case series enrolled only 12 children.", "category": "x"},
                      [{"claim_id": "c10", "source_id": "src-wake"}], {"src-wake": src})
    assert out2["support"] == "FIGURE_BOUND"


def test_every_row_of_the_live_withhold_register_is_a_real_mmr_claim_with_a_reason():
    from verify import publish
    reg = json.loads(publish.WITHHELD_CLAIMS.read_text())
    rec = json.loads((Path(publish.PUBLISHED) / "mmr-vaccine-autism" / "latest.json").read_text())
    ids = {c["claim_id"] for c in rec["claims"]}
    for cid, row in reg["claims"].items():
        assert cid in ids, cid
        assert row["reason"] and row["checked_against"] and row["withheld_by"] and row["withheld_on"] and row["ruled_by"]


def test_the_scope_statement_is_frozen_into_the_record_from_the_operators_file():
    """The page renders the record's copy of the operator's ratified scope
    statement, never the file: the statement a reader sees is the one frozen
    with the record it describes. A topic without a file gets None."""
    from verify import publish
    r = publish.scope_statement("mmr-vaccine-autism")
    assert r and r["source"] == "data/verify/scope/mmr-vaccine-autism.md"
    assert r["text"].startswith("This page covers the epidemiological evidence on MMR vaccination and autism")
    assert "quashing the GMC's findings against Professor Walker-Smith" in r["text"]
    assert "competing-interests correction to its editorial" in r["text"]
    assert r["sha256"] == __import__("hashlib").sha256(r["text"].encode()).hexdigest()
    assert publish.scope_statement("no-such-topic") is None
