"""Law adapter acceptance, both directions (design doc §9).

Negatives: the twelve wrong citations from the ten appeal letters of
2026-09-14, each asserted to fail on the ONE kind it should -- ORC 3901.38
passes HEADING and fails FIGURE; OAC 3901-1-54 passes HEADING and fails
APPLICABILITY; 42 CFR 424.5(a)(6) passes HEADING (its paragraph says what the
letter said) and fails APPLICABILITY (Medicare rule, commercial payer); the
unnumbered "Department of Insurance claims processing regulations" fails at
resolve. Positives: the seven right ones plus ORC 3901.381 ("thirty days" /
"forty-five days") and 3901.389 ("eighteen per cent"), which exercise
word-number normalisation. Two context negatives: a right provision cited
against the wrong payer type, and the right Ohio section for a Texas practice.

Replayed from tests/verify/fixtures/http, recorded live on 2026-09-14. The
manual entries need pdftotext; without it they are skipped, not passed.

Run: python3 -m pytest backend/tests/verify/test_golden_law.py -q
"""
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("VERIFY_CACHE_DIR", str(Path(__file__).parent / "fixtures" / "http"))
from verify import http  # noqa: E402
http.CACHE_DIR = Path(os.environ["VERIFY_CACHE_DIR"])
from verify.bind import bind_all  # noqa: E402
from verify.law import fetch, identify, resolve  # noqa: E402
from verify.types import Context, Exists  # noqa: E402

GOLDEN = json.loads((Path(__file__).parent / "golden_law.json").read_text())
NEEDS_PDF = ("cms_iom", "ncci")


def _run(entry):
    ident = identify(entry["cite"])
    if ident is None:
        return None, None, None, []
    if ident.system in NEEDS_PDF and not shutil.which("pdftotext"):
        pytest.skip("pdftotext not installed; manual entries cannot be extracted here")
    res = resolve(ident)
    doc = fetch(res)
    ok, bs = bind_all(entry["assertion"], res, doc, Context(**entry["context"]),
                      characterisation=entry["characterisation"])
    return ident, res, ok, bs


@pytest.mark.parametrize("entry", GOLDEN["negatives"], ids=[e["cite"][:40] for e in GOLDEN["negatives"]])
def test_each_wrong_citation_fails_on_the_kind_it_should(entry):
    ident, res, ok, bs = _run(entry)
    if entry["must_fail"] == "RESOLVE":
        assert ident is None or res.exists != Exists.EXISTS
        return
    assert res.exists == Exists.EXISTS, "the provision exists; the error is what it says"
    assert not ok
    failed = {b.kind.value for b in bs if not b.ok}
    assert entry["must_fail"] in failed, (failed, [(b.kind.value, b.reason) for b in bs])
    for k in entry.get("must_pass", []):
        assert k not in failed, f"{k} must pass so the failure lands on {entry['must_fail']}"


@pytest.mark.parametrize("entry", GOLDEN["positives"], ids=[e["cite"][:40] for e in GOLDEN["positives"]])
def test_each_right_citation_passes_every_kind(entry):
    ident, res, ok, bs = _run(entry)
    assert ident is not None and res.exists == Exists.EXISTS
    assert ok, [(b.kind.value, b.reason) for b in bs if not b.ok]


@pytest.mark.parametrize("entry", GOLDEN["context_negatives"], ids=[e["cite"][:30] + "/" + e["context"]["payer_type"] + "/" + e["context"]["state"] for e in GOLDEN["context_negatives"]])
def test_a_right_provision_in_the_wrong_context_fails_applicability(entry):
    ident, res, ok, bs = _run(entry)
    assert not ok and "APPLICABILITY" in {b.kind.value for b in bs if not b.ok}


def test_false_negative_rate_is_reported():
    refused = 0
    for entry in GOLDEN["positives"]:
        ident, res, ok, bs = _run(entry)
        refused += 0 if ok else 1
    print(f"\nlaw false-negative rate: {refused}/{len(GOLDEN['positives'])}")
    assert refused == 0


def test_3901_38_specifically_passes_heading_and_fails_figure():
    entry = next(e for e in GOLDEN["negatives"] if "3901.38" in e["cite"] and "3901.381" not in e["cite"])
    _, _, ok, bs = _run(entry)
    by = {b.kind.value: b.ok for b in bs}
    assert by["HEADING"] is True and by["FIGURE"] is False and not ok
