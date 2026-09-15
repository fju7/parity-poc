"""The publish gate on links to already-changed sources (ruling of 2026-09-14).

A claim whose SUPPORT was retracted (or corrected, superseded, amended)
before the freeze is UNSUPPORTED -- refused at publish, not published with a
warning. A claim whose SUBJECT is the retracted work stays publishable. So
the red marker only ever means "this changed after we froze it". Also the
link-role rule and its audit record: which rule fired and what matched.

Wakefield 1998 is the reference case, replayed from fixtures.
"""
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
