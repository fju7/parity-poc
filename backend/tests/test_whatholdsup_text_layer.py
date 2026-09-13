"""A declared-defective text layer: cannot evaluate, never present (13 Sept 2026).

S003's PDF maps the dash in 'Lan-DeMets' / 'O'Brien-Fleming' to the letter
'e'. The defect is DECLARED on the rendition's record by a person who rendered
the page; nothing sets it automatically. With it declared, a span the layer
cannot carry is UNDETERMINED with the reason in words -- neither absent nor
present -- and a quote genuinely not in the paper must never pass as present.
A second rendition with a sound layer lifts it.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
spec = importlib.util.spec_from_file_location("spancheck_real", WHU / "spancheck.py")
real_SC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(real_SC)


# ---------------------------------------------------------------------------
# A declared-defective text layer: cannot evaluate, never present (13 Sept 2026)
# ---------------------------------------------------------------------------

def test_a_declared_defective_rendition_reports_cannot_evaluate_not_absent(monkeypatch):
    """S003's PDF maps the dash in 'Lan–DeMets' to the letter 'e'. With the
    defect declared on the record, a span the layer cannot carry is neither
    absent nor present: UNDETERMINED, with the reason in readable words."""
    monkeypatch.setattr(real_SC.store, "held", lambda slug: {
        "S9": {"file": "x.pdf", "text_layer": {"state": "defective", "reason": "dash -> e"}}})
    monkeypatch.setattr(real_SC, "_text", lambda slug, sid: "Lane DeMets spending function")
    monkeypatch.setattr(real_SC, "_texts", lambda slug, sid: [("x.pdf", "Lane DeMets spending function")])
    v, why = real_SC.b2_present("Lan–DeMets spending function", "t", "S9")
    assert v == real_SC.UNDETERMINED and "cannot evaluate" in why and "dash -> e" in why


def test_a_genuinely_absent_quote_never_passes_as_present_on_a_defective_layer(monkeypatch):
    """The counterfactual that makes the declaration honest: a broken layer
    loses characters, it does not invent them, so a quote that is truly not
    in the paper must come back cannot-evaluate -- never ok."""
    monkeypatch.setattr(real_SC.store, "held", lambda slug: {
        "S9": {"file": "x.pdf", "text_layer": {"state": "defective", "reason": "dash -> e"}}})
    monkeypatch.setattr(real_SC, "_text", lambda slug, sid: "Lane DeMets spending function")
    monkeypatch.setattr(real_SC, "_texts", lambda slug, sid: [("x.pdf", "Lane DeMets spending function")])
    v, _ = real_SC.b2_present("this sentence is not in the paper at all", "t", "S9")
    assert v is not True and v == real_SC.UNDETERMINED
    # and a span the layer DOES carry is still present, not undetermined
    assert real_SC.b2_present("spending function", "t", "S9")[0] is True


def test_a_second_sound_rendition_lifts_the_declaration(monkeypatch):
    monkeypatch.setattr(real_SC.store, "held", lambda slug: {
        "S9": {"file": "x.pdf", "text_layer": {"state": "defective", "reason": "dash -> e"},
               "also_held": [{"file": "y.html"}]}})
    monkeypatch.setattr(real_SC, "_text", lambda slug, sid: "Lane DeMets spending function")
    monkeypatch.setattr(real_SC, "_texts", lambda slug, sid: [("x.pdf", "Lane DeMets spending function"),
                                                              ("y.html", "Lan–DeMets spending function")])
    assert real_SC.b2_present("Lan–DeMets spending function", "t", "S9")[0] is True
    assert real_SC.b2_present("not in either", "t", "S9")[0] is False


# ---------------------------------------------------------------------------
# The same property one level up: findings.quote_is_in_source (13 Sept 2026)
# ---------------------------------------------------------------------------

def _findings_module():
    import findings as F
    return F


def test_findings_quote_check_reports_cannot_evaluate_on_a_defective_layer(monkeypatch):
    """The directive's counterfactual, at the level a finding is settled: a
    quote genuinely absent from the source, against a rendition carrying
    text_layer: defective, must report cannot-evaluate and never ok."""
    F = _findings_module()
    monkeypatch.setattr(F.store, "held", lambda slug: {"S9": {"file": "x.pdf"}})
    monkeypatch.setattr(F.SC, "_texts", lambda slug, sid: [("x.pdf", "Lane DeMets spending function")])
    monkeypatch.setattr(F.SC, "defective_renditions", lambda slug, sid: (True, "dash -> e"))
    ok, why = F.quote_is_in_source("t", "S9", "this sentence is not in the paper at all")
    assert ok is F.SC.UNDETERMINED and ok is not True
    assert "cannot evaluate" in why and "dash -> e" in why
    # the same absent quote against a SOUND layer is plainly absent -- the
    # declaration is what changes the verdict, and only the declaration
    monkeypatch.setattr(F.SC, "defective_renditions", lambda slug, sid: (False, ""))
    ok2, why2 = F.quote_is_in_source("t", "S9", "this sentence is not in the paper at all")
    assert ok2 is False and "not in S9" in why2


def test_findings_check_puts_an_unevaluable_quote_in_a_warn_row_not_a_stop(monkeypatch):
    F = _findings_module()
    report = {"claims": [{"id": "c1", "kind": "characterisation", "quote": "x", "but": "y"}],
              "verdicts": {"c1": {"verdict": "WRONG_VALUE", "what": "y"}}}
    monkeypatch.setattr(F, "open_findings", lambda r: [{"id": "c1", "kind": "claim", "verdict": "WRONG_VALUE", "what": "y"}])
    monkeypatch.setattr(F, "load", lambda slug: {"findings": [{"id": "c1", "decision": "accepted", "source_id": "S9", "quote": "Lan–DeMets", "why": "w", "by": "b"}]})
    monkeypatch.setattr(F, "save", lambda slug, doc: None)
    monkeypatch.setattr(F, "attestation_for", lambda slug, c: None)
    monkeypatch.setattr(F, "quote_is_in_source", lambda slug, sid, q: (F.SC.UNDETERMINED, "cannot evaluate -- rendition text layer defective"))
    rows = {r[0]: r for r in F.check("t", report)}
    assert rows["findings settled by a document"][1] == F.OK
    assert rows["those quotations are in the bytes"][1] == F.OK
    assert rows["quotations this check cannot evaluate"][1] == F.WARN
    assert "defective text layer" in rows["quotations this check cannot evaluate"][2]


# ---------------------------------------------------------------------------
# A partial string match is neither live nor settled (13 Sept 2026, inf-10)
# ---------------------------------------------------------------------------

def test_a_revised_attacked_sentence_is_partly_not_live_and_not_moot():
    F = _findings_module()
    attacked = ("Two randomised trials have tested one of these drugs against another — both "
                "ribociclib against palbociclib, both outside the first-line setting, and neither separated them.")
    revised_page = ("Two randomised trials have tested one of these drugs against another — both "
                    "ribociclib against palbociclib, neither in the population the guideline describes. "
                    "One found no significant difference; the other never reported.")
    assert F._attacked_sentence_state(attacked, revised_page) == "partly"
    assert F._attacked_sentence_state(attacked, attacked) == "live"
    assert F._attacked_sentence_state(attacked, "nothing of it remains") == "gone"


def test_the_attacked_claim_surviving_under_different_words_does_not_settle(monkeypatch):
    """The counterfactual: the wording was revised but the attacked claim
    ('neither separated them') survives as 'and neither told them apart'. A
    prefix match must NOT record a decision -- not moot, not closed -- and must
    not report live either. It reports partly and leaves the decision empty."""
    F = _findings_module()
    attacked = ("Two randomised trials have tested one of these drugs against another — both "
                "ribociclib against palbociclib, both outside the first-line setting, and neither separated them.")
    page = ("Two randomised trials have tested one of these drugs against another — both "
            "ribociclib against palbociclib, in other settings, and neither told them apart.")
    report = {"claims": [], "verdicts": {}, "inferences": [{"quote": attacked, "problem": "p", "class": "CONTRADICTION"}]}
    monkeypatch.setattr(F, "open_findings", lambda r: [{"id": "inf-1", "kind": "inference", "verdict": "CONTRADICTION", "what": "p"}])
    monkeypatch.setattr(F, "load", lambda slug: {"findings": []})
    saved = {}
    monkeypatch.setattr(F, "save", lambda slug, doc: saved.update(doc))
    monkeypatch.setattr(F, "_page_plain", lambda slug: page)
    out = F.retest("t", report)
    assert out["partly"] == ["inf-1"] and out["live"] == [] and out["moot"] == [] and out["closed"] == []
    rec = saved["findings"][0]
    assert rec["decision"] == "" and rec["retest"]["outcome"] == "partly"
    assert "disposition naming the current sentence" in rec["retest"]["result"]


def test_a_partly_finding_is_a_warn_row_not_a_stop(monkeypatch):
    F = _findings_module()
    report = {"claims": [], "verdicts": {}}
    monkeypatch.setattr(F, "open_findings", lambda r: [{"id": "inf-1", "kind": "inference", "verdict": "CONTRADICTION", "what": "p"}])
    monkeypatch.setattr(F, "load", lambda slug: {"findings": [{"id": "inf-1", "decision": "",
                                                               "retest": {"outcome": "partly", "result": "partly still in the text -- a disposition naming the current sentence is required"}}]})
    monkeypatch.setattr(F, "save", lambda slug, doc: None)
    monkeypatch.setattr(F, "attestation_for", lambda slug, c: None)
    rows = {r[0]: r for r in F.check("t", report)}
    assert rows["findings settled by a document"][1] == F.OK
    assert rows["findings partly still in the text"][1] == F.WARN
    assert "inf-1" in rows["findings partly still in the text"][2]
