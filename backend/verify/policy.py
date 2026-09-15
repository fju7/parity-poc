"""The shared assertion policy: which surface may emit which class of
assertion, at which tier, and one check() that runs at a response boundary.

Design: docs/shared-assertion-policy-phase-a-inventory.md §C-§D, approved
2026-09-15 with four amendments (lint covers all string literals in backend/
and frontend/; the AST-discovered surface set is reconciled against POLICY by
a test; UNCHECKED has a consumer; PHI is lifted out to its own document).

THREE TIERS
    WITHHOLD  the material is never handed to the model, so its appearance
              in the output is a bug: any candidate of the class is a refusal.
              The strongest control in the repo (Health PH-4a.3) is this tier.
    GATE      the surface must emit the class, so every candidate must BIND to
              something the system holds: an allow-listed provision, an
              identifier in the evidence handed over, a figure present in the
              source document or in the JSON we computed, a descriptor in a
              table we keep. What does not bind is refused. What CANNOT be
              judged -- a figure read from an image with no text layer -- is
              UNCHECKED, which is never a pass and is reported as such.
    EXEMPT    the class cannot appear (a column mapping, a document type).

THE TABLE IS HAND-MAINTAINED, which is the structure that let Provider diverge
from Health. tests/verify/test_policy_discovery.py reconciles it against an AST
walk of backend/ in both directions -- a discovered surface with no entry
fails, a stale entry fails, and a module importing anthropic outside the
approved wrappers fails -- so the table cannot silently fall behind the code.

No model is called here. Every decision is string comparison against held
material, through the binders in this package.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterator

from .extract import AssertionClass, Candidate, extract
from .numbers import canonical_numbers, stated_figures, figure_matches, _canon
from .text import agreement, normalise, GENERIC_BOILERPLATE
from .types import Document, Identifier, Provenance


class Tier(str, Enum):
    WITHHOLD = "withhold"
    GATE = "gate"
    EXEMPT = "exempt"


@dataclass
class SurfacePolicy:
    tiers: dict[AssertionClass, Tier]
    product: str
    note: str = ""
    # Which of the surface's output fields carry model prose. check() walks
    # every string in the output regardless; this documents the intent.
    fields: tuple[str, ...] = ()
    # Identifier sub-kinds that REFUSE rather than flag under WITHHOLD/GATE.
    # bare_pmid (any 7-8 digit number) is a flag by default: claim ids and
    # invoice numbers share its shape. Health's letter body keeps it strict,
    # as _validate_evidence_claims always has.
    strict_identifier_kinds: frozenset = frozenset({"doi", "pmid", "pmcid", "nct", "fda_pma", "journal_cite"})
    # Output fields the walk skips: free-text descriptors on an extraction row
    # ("description": "Office visit, level 3") are not assertions about the
    # source in the way the code and the rate are.
    ignore_fields: tuple = ()
    # Word-form counting numbers ("two theories", "six years before") in a
    # PARAPHRASE are the model counting or doing arithmetic over what it was
    # handed, not quantities the source must state. "flag" reports them without
    # refusing; "refuse" (the default, right for letters and extraction) does
    # not. Measured on mmr-vaccine-autism 2026-09-15: 22 of 26 unbound figures
    # in 118 plain summaries were counting words; the other 4 were added facts.
    word_figures: str = "refuse"          # "refuse" | "flag"  (word-form values <= 12 only)
    # Whether check() is actually attached at this surface's response boundary
    # today. A GATE entry with wired=False is a declared, unenforced tier;
    # tests/verify/test_policy_discovery.py lists them so the set only shrinks.
    wired: bool = False


# ---------------------------------------------------------------------------
# Held material: what the system handed the model or holds about the request.
# ---------------------------------------------------------------------------
@dataclass
class Held:
    allowed: list = field(default_factory=list)          # verify.allowlist.Allowed for LEGAL
    identifiers: set = field(default_factory=set)        # normalised ids the system handed over
    documents: list = field(default_factory=list)        # verify.types.Document: text figures/spans must be in
    inputs: dict = field(default_factory=dict)           # JSON the system computed and handed over
    tables: dict = field(default_factory=dict)           # {"CPT": {"99213": "Office visit..."}, "CARC": {...}}
    named_ok: set = field(default_factory=set)           # lexicon terms this surface may name (e.g. {"caa"})

    def corpus_text(self) -> str:
        parts = [d.text for d in self.documents if d.text_layer == "DECLARED_SOUND"]
        if self.inputs:
            # ensure_ascii=False: json.dumps would turn "£435,643" into
            # "\u00a3435,643", and a digit behind a word character is not a
            # figure to the extractor. Found on mmr-vaccine-autism 2026-09-15.
            parts.append(json.dumps(self.inputs, default=str, ensure_ascii=False))
        return "\n".join(parts)

    def has_unreadable_document(self) -> bool:
        return any(d.text_layer != "DECLARED_SOUND" for d in self.documents)


@dataclass
class Finding:
    cls: AssertionClass
    field: str
    text: str
    ok: bool | None            # True bound / False refused / None UNCHECKED
    mode: str                  # "absent" (WITHHOLD) | "bound" (GATE)
    reason: str = ""
    severity: str = "refuse"   # "refuse" | "flag" | "unchecked"
    kind: str = ""

    def to_dict(self) -> dict:
        return {"class": self.cls.value, "field": self.field, "text": self.text, "kind": self.kind,
                "ok": self.ok, "mode": self.mode, "severity": self.severity, "reason": self.reason}


@dataclass
class Verdict:
    surface: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def refusals(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "refuse" and f.ok is False]

    @property
    def flags(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "flag"]

    @property
    def unchecked(self) -> list[Finding]:
        return [f for f in self.findings if f.ok is None]

    @property
    def ok(self) -> bool:
        """No refusal. UNCHECKED does not make a verdict ok; it makes it not
        verified -- callers must surface .unchecked, never treat ok as verified."""
        return not self.refusals

    @property
    def verified(self) -> bool:
        return self.ok and not self.unchecked

    def to_dict(self) -> dict:
        """The record that travels with the output: stored beside it and
        returned in the API response, so UNCHECKED has a consumer."""
        return {
            "surface": self.surface,
            "ok": self.ok,
            "verified": self.verified,
            "refused": [f.to_dict() for f in self.refusals],
            "unchecked": [f.to_dict() for f in self.unchecked],
            "flags": [f.to_dict() for f in self.flags],
            "checked": sum(1 for f in self.findings if f.ok is True),
        }

    def note(self) -> str:
        """One line for a reader: what was refused / what could not be checked."""
        parts = []
        if self.refusals:
            parts.append(f"{len(self.refusals)} refused: " + "; ".join(f"{f.text} [{f.reason}]" for f in self.refusals[:6]))
        if self.unchecked:
            parts.append(f"{len(self.unchecked)} could not be verified: " + "; ".join(f"{f.text}" for f in self.unchecked[:6])
                         + f" [{self.unchecked[0].reason}]")
        return " | ".join(parts)


# ---------------------------------------------------------------------------
# walking an output
# ---------------------------------------------------------------------------
def walk_strings(output: Any, path: str = "", ignore: tuple = ()) -> Iterator[tuple[str, str]]:
    """Every string in `output` with its path. Numbers are yielded as strings
    too: an extracted rate is a float, and a float the model made up is the
    whole point. Booleans and None are not values a model asserts."""
    if path and ignore and any(path == f or path.endswith("." + f) for f in ignore):
        return
    if isinstance(output, bool) or output is None:
        return
    if isinstance(output, (int, float)):
        yield (path or "$", repr(output) if isinstance(output, float) else str(output))
    elif isinstance(output, str):
        yield (path or "$", output)
    elif isinstance(output, dict):
        for k, v in output.items():
            yield from walk_strings(v, f"{path}.{k}" if path else str(k), ignore)
    elif isinstance(output, (list, tuple)):
        for i, v in enumerate(output):
            yield from walk_strings(v, f"{path}[{i}]", ignore)


def _blank(text: str, cands: list[Candidate]) -> str:
    """Replace other-class spans with spaces so their digits are not read as
    figures (a section number is not a figure the sentence commits to)."""
    t = list(text)
    for c in cands:
        if c.end > c.start:
            for i in range(c.start, min(c.end, len(t))):
                t[i] = " "
    return "".join(t)


# ---------------------------------------------------------------------------
# binders, one per class
# ---------------------------------------------------------------------------
def _bind_legal(field_name: str, text: str, held: Held) -> list[Finding]:
    from utils.citation_gate import check_letter
    out = []
    for c in check_letter(text, held.allowed or None):
        out.append(Finding(AssertionClass.LEGAL_PROVISION, field_name, c.text, False, "bound",
                           "not on this letter's allow-list" if held.allowed else "no allow-list: every citation is refused",
                           kind=c.family))
    # anything the gate accepted is bound
    from utils.citation_gate import find_citations
    refused = {(f.text.split(" [")[0]) for f in out}
    for c in find_citations(text):
        if c.text not in refused:
            out.append(Finding(AssertionClass.LEGAL_PROVISION, field_name, c.text, True, "bound", "allow-listed and bound", kind=c.family))
    return out


def _bind_identifiers(field_name: str, text: str, held: Held, policy: SurfacePolicy) -> list[Finding]:
    out = []
    for c in extract(AssertionClass.IDENTIFIER, text):
        strict = c.kind in policy.strict_identifier_kinds
        if c.kind in ("doi", "pmid", "pmcid", "nct", "fda_pma") and c.value.lower() in {i.lower() for i in held.identifiers}:
            out.append(Finding(AssertionClass.IDENTIFIER, field_name, c.text, True, "bound", "identifier was handed to the model", kind=c.kind))
        elif strict:
            out.append(Finding(AssertionClass.IDENTIFIER, field_name, c.text, False, "bound",
                               "identifier not among those the system handed over" + (f"; {c.extra}" if c.extra else ""), kind=c.kind))
        else:
            out.append(Finding(AssertionClass.IDENTIFIER, field_name, c.text, False, "bound",
                               "identifier-shaped; review" + (f"; {c.extra}" if c.extra else ""), severity="flag", kind=c.kind))
    return out


def _bind_named(field_name: str, text: str, held: Held) -> list[Finding]:
    out = []
    corpus = normalise(held.corpus_text())
    for c in extract(AssertionClass.NAMED_SOURCE, text):
        if c.kind in held.named_ok:
            out.append(Finding(AssertionClass.NAMED_SOURCE, field_name, c.text, True, "bound", "permitted for this surface", kind=c.kind))
        elif normalise(c.text) in corpus or _named_alias_present(c.kind, held):
            out.append(Finding(AssertionClass.NAMED_SOURCE, field_name, c.text, True, "bound", "named in the material handed over", kind=c.kind))
        else:
            out.append(Finding(AssertionClass.NAMED_SOURCE, field_name, c.text, False, "bound",
                               "names a source, body, statute or status not in the material handed over", kind=c.kind))
    return out


def _named_alias_present(term: str, held: Held) -> bool:
    """'Centers for Disease Control' binds to 'CDC' in the held material: the
    lexicon term, not the surface spelling, is what must be present."""
    from .extract import _NAMED_RX
    rx = _NAMED_RX.get(term)
    return bool(rx and rx.search(held.corpus_text()))


def _bind_figures(field_name: str, text: str, held: Held, other: list[Candidate], policy: "SurfacePolicy | None" = None) -> list[Finding]:
    out = []
    blanked = _blank(text, other)
    # Dates are CHRONOLOGY's business, not FIGURE's: "September 15, 2026" is
    # not a quantity the held material must state (the letterhead date is
    # stamped by code after generation). Blank every explicit date span.
    from .chronology import _DATE
    blanked = _DATE.sub(lambda m: " " * len(m.group(0)), blanked)
    cands = extract(AssertionClass.FIGURE, blanked)
    if not cands:
        return out
    corpus = held.corpus_text()
    if not corpus.strip():
        reason = ("source has no text layer; figures cannot be checked" if held.has_unreadable_document()
                  else "nothing held to check figures against")
        return [Finding(AssertionClass.FIGURE, field_name, c.text, None, "bound", reason, severity="unchecked", kind=c.kind)
                for c in cands]
    have = canonical_numbers(corpus)
    stated = {_canon(f["value"]): f for f in stated_figures(blanked)}
    for c in cands:
        if c.value in have:
            out.append(Finding(AssertionClass.FIGURE, field_name, c.text, True, "bound", "present in held material", kind=c.kind))
            continue
        f = stated.get(c.value)
        hit = figure_matches(f, have) if f else None
        if not hit and f is not None and held.inputs and f["precision"] == 1:
            # A number RESTATED from our own computed inputs may be rounded to the
            # unit ("$512" for 512.4, "71st" for 71.2). Documents get no such
            # tolerance: what a source says is what it says.
            hit = _rounds_to(f["value"], canonical_numbers(json.dumps(held.inputs, default=str, ensure_ascii=False)))
        if hit:
            out.append(Finding(AssertionClass.FIGURE, field_name, c.text, True, "bound", f"matches {hit} at stated precision", kind=c.kind))
        elif policy is not None and policy.word_figures == "flag" and c.kind == "words" and _small(c.value) \
                and not _has_unit(blanked, c):
            out.append(Finding(AssertionClass.FIGURE, field_name, c.text, False, "bound",
                               "counting word not in the held material; a paraphrase count, reported not refused",
                               severity="flag", kind=c.kind))
        else:
            out.append(Finding(AssertionClass.FIGURE, field_name, c.text, False, "bound", "not in the held material", kind=c.kind))
    if held.has_unreadable_document():
        # part of the source could not be read: a refusal here may be a false
        # negative, so downgrade refusals to UNCHECKED rather than pass them
        for f in out:
            if f.ok is False:
                f.ok, f.severity, f.reason = None, "unchecked", "not in the readable text; part of the source has no text layer"
    return out


# A counting word followed by a unit is a quantity, not a count: "six years
# before the retraction" (2004 -> 2010, the 2010 from the model's memory) is
# arithmetic yielding a figure nothing handed over contains. Found on
# mmr-vaccine-autism claim 5b3bff25, 2026-09-15.
_UNIT_AFTER = re.compile(r"^\s*(?:years?|months?|weeks?|days?|decades?|hours?|percent|per\s?cent|%|times|fold|"
                         r"million|billion|thousand|hundred|patients?|children|participants?|cases?|studies|trials?)\b", re.I)


def _has_unit(text: str, c: Candidate) -> bool:
    """Is the word-form figure followed by a unit or a counted noun in the text?"""
    m = re.search(r"\b(?:" + "|".join(re.escape(w) for w in _WORD_FORMS.get(c.value, ())) + r")\b\s*(?:\(\d+\))?", text, re.I) if _WORD_FORMS.get(c.value) else None
    if not m:
        return False
    return bool(_UNIT_AFTER.match(text[m.end():]))


_WORD_FORMS = {str(v): (k,) for k, v in {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
                                          "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}.items()}
_WORD_FORMS["0.5"] = ("half",)


def _small(value: str) -> bool:
    try:
        return 0 <= float(value) <= 12
    except ValueError:
        return False


def _rounds_to(value, have: set[str]) -> str | None:
    from decimal import Decimal, InvalidOperation
    for dv in have:
        try:
            if Decimal(dv).quantize(Decimal(1), rounding="ROUND_HALF_UP") == value:
                return dv
        except InvalidOperation:
            continue
    return None


def _bind_coded(field_name: str, text: str, held: Held) -> list[Finding]:
    out = []
    for c in extract(AssertionClass.CODED_DESCRIPTOR, text):
        table = held.tables.get(c.kind) or {}
        ours = table.get(c.value)
        if ours is None:
            out.append(Finding(AssertionClass.CODED_DESCRIPTOR, field_name, c.text, None, "bound",
                               f"no held descriptor for {c.kind} {c.value}", severity="unchecked", kind=c.kind))
            continue
        ratio, shared = agreement(c.extra, ours, GENERIC_BOILERPLATE)
        if shared:
            out.append(Finding(AssertionClass.CODED_DESCRIPTOR, field_name, c.text, True, "bound", "agrees with held descriptor: " + ", ".join(sorted(shared)), kind=c.kind))
        else:
            out.append(Finding(AssertionClass.CODED_DESCRIPTOR, field_name, c.text, False, "bound",
                               f"descriptor shares no word with the held descriptor ({ours[:60]!r})", kind=c.kind))
    return out


def _absent(cls: AssertionClass, field_name: str, text: str, policy: SurfacePolicy, other: list[Candidate]) -> list[Finding]:
    """WITHHOLD: any candidate is a refusal (identifier flags per policy)."""
    out = []
    src = _blank(text, other) if cls is AssertionClass.FIGURE else text
    for c in extract(cls, src):
        if cls is AssertionClass.IDENTIFIER and c.kind not in policy.strict_identifier_kinds:
            out.append(Finding(cls, field_name, c.text, False, "absent", "identifier-shaped in a surface that was handed no identifiers; review", severity="flag", kind=c.kind))
        else:
            out.append(Finding(cls, field_name, c.text, False, "absent", "class is withheld from this surface; it should not appear", kind=c.kind))
    return out


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------
def check(surface: str, output: Any, held: Held | None = None, *, policy_table: dict | None = None) -> Verdict:
    """Run the surface's policy over every string in `output`.

    `output` is the assembled response dict (or a string). Walking the whole
    dict is deliberate: provider_appeals' escalation_path and cms_references
    reached the caller for five months without passing the gate that
    covered letter_text.
    """
    table = policy_table if policy_table is not None else POLICY
    if surface not in table:
        raise KeyError(f"surface {surface!r} has no policy entry; see tests/verify/test_policy_discovery.py")
    pol = table[surface]
    held = held or Held()
    verdict = Verdict(surface)
    for field_name, text in walk_strings(output, ignore=pol.ignore_fields):
        if not text or not text.strip():
            continue
        other = (extract(AssertionClass.LEGAL_PROVISION, text) + extract(AssertionClass.IDENTIFIER, text)
                 + extract(AssertionClass.CODED_DESCRIPTOR, text))
        for cls, tier in pol.tiers.items():
            if tier is Tier.EXEMPT:
                continue
            if tier is Tier.WITHHOLD:
                verdict.findings.extend(_absent(cls, field_name, text, pol, other))
                continue
            if cls is AssertionClass.LEGAL_PROVISION:
                verdict.findings.extend(_bind_legal(field_name, text, held))
            elif cls is AssertionClass.IDENTIFIER:
                verdict.findings.extend(_bind_identifiers(field_name, text, held, pol))
            elif cls is AssertionClass.NAMED_SOURCE:
                verdict.findings.extend(_bind_named(field_name, text, held))
            elif cls is AssertionClass.FIGURE:
                verdict.findings.extend(_bind_figures(field_name, text, held, other, pol))
            elif cls is AssertionClass.CODED_DESCRIPTOR:
                verdict.findings.extend(_bind_coded(field_name, text, held))
    return verdict


def check_prompt_payload(surface: str, payload: Any, *, policy_table: dict | None = None) -> list[Finding]:
    """Input-side assertion for WITHHOLD classes: the material handed to the
    model must itself contain no instance of a withheld class. This is what
    makes "withheld" a checked fact rather than an assumption (the
    _assert_no_phi shape)."""
    table = policy_table if policy_table is not None else POLICY
    pol = table[surface]
    out = []
    for field_name, text in walk_strings(payload):
        other = (extract(AssertionClass.LEGAL_PROVISION, text) + extract(AssertionClass.IDENTIFIER, text)
                 + extract(AssertionClass.CODED_DESCRIPTOR, text))
        for cls, tier in pol.tiers.items():
            if tier is Tier.WITHHOLD:
                for f in _absent(cls, field_name, text, pol, other):
                    f.reason = "withheld class present in the PROMPT PAYLOAD: " + f.reason
                    out.append(f)
    return out


# ---------------------------------------------------------------------------
# THE TABLE
# Keys are "module::function" for the function that directly calls a model
# wrapper or the SDK (a "surface"); tests/verify/test_policy_discovery.py
# derives the same keys from the AST and reconciles both ways.
# ---------------------------------------------------------------------------
L, I, N, F, C = (AssertionClass.LEGAL_PROVISION, AssertionClass.IDENTIFIER, AssertionClass.NAMED_SOURCE,
                 AssertionClass.FIGURE, AssertionClass.CODED_DESCRIPTOR)
W, G, X = Tier.WITHHOLD, Tier.GATE, Tier.EXEMPT

_NARRATIVE = {L: W, I: W, N: W, F: G, C: W}      # handed computed numbers, nothing else
_PROSE = {L: W, I: G, N: G, F: G, C: X}          # Signal prose about bound claims
_EXTRACTION = {L: X, I: X, N: X, F: G, C: X}     # reads numbers out of an upload
_EXTRACTION_IGNORE = ("description", "notes", "plan_name", "payer_name", "drug_name", "generic_name", "therapeutic_class", "provider_name", "insurance_name", "network_type", "date_range")
_MAPPING = {L: X, I: X, N: X, F: X, C: X}        # emits no assertion class

POLICY: dict[str, SurfacePolicy] = {
    # ---- Provider ----------------------------------------------------------
    "routers.provider_appeals::_gated_letter": SurfacePolicy(
        {L: G, I: W, N: G, F: G, C: G}, "provider", fields=("letter_text", "letter_html", "cms_references", "appeal_strength_reason", "escalation_path", "attach_documentation"),
        note="reference implementation; LEGAL via check_letter + allow-list; all six fields walked; NAMED/FIGURE bind to the prompt + prompt_data (prompt-typed material is TYPED and reviewed by the literal lint); CODED is UNCHECKED until a CPT table is held", wired=True),
    "routers.provider_audit::extract_fee_schedule_pdf": SurfacePolicy(_EXTRACTION, "provider", note="P2", ignore_fields=_EXTRACTION_IGNORE, wired=True),
    "routers.provider_audit::extract_fee_schedule_text": SurfacePolicy(_EXTRACTION, "provider", note="P2", ignore_fields=_EXTRACTION_IGNORE, wired=True),
    "routers.provider_audit::extract_fee_schedule_image": SurfacePolicy(_EXTRACTION, "provider", note="P2; image -> UNCHECKED", ignore_fields=_EXTRACTION_IGNORE, wired=True),
    "routers.provider_audit::analyze_contract": SurfacePolicy(_NARRATIVE, "provider", note="P3 scorecard narrative"),
    "routers.provider_audit::_run_coding_analysis_from_835": SurfacePolicy(_NARRATIVE, "provider", note="P4"),
    "routers.provider_audit::analyze_coding": SurfacePolicy(_NARRATIVE, "provider", note="P4"),
    "routers.provider_audit::parse_837": SurfacePolicy(_EXTRACTION, "provider", note="P5 CSV fallback", ignore_fields=_EXTRACTION_IGNORE),
    "routers.provider_audit::analyze_denials": SurfacePolicy({L: W, I: W, N: W, F: G, C: G}, "provider", note="P6; letter + totals removed A.5"),
    "routers.provider_shared::_run_analysis_for_payer": SurfacePolicy({L: W, I: W, N: W, F: G, C: G}, "provider", note="P6 monthly path"),
    "routers.provider_audit::generate_audit_report": SurfacePolicy(_NARRATIVE, "provider", note="P7 PDF narratives"),
    "routers.provider_trends::_generate_trend_narrative": SurfacePolicy(_NARRATIVE, "provider", note="P8"),
    # ---- Billing -----------------------------------------------------------
    "routers.billing_contracts::analyze_contract": SurfacePolicy(_EXTRACTION, "billing", note="B1", ignore_fields=_EXTRACTION_IGNORE, wired=True),
    "routers.billing_contracts::analyze_all_contracts": SurfacePolicy(_EXTRACTION, "billing", note="B1 bulk", ignore_fields=_EXTRACTION_IGNORE, wired=True),
    # ---- Employer ----------------------------------------------------------
    "routers.employer_benchmark::employer_benchmark": SurfacePolicy(_NARRATIVE, "employer", note="E1", wired=True),
    "routers.employer_claims::employer_claims_check": SurfacePolicy(_NARRATIVE, "employer", note="E2 mapping + E3 narrative/action plan"),
    "routers.employer_claims::employer_contract_parse": SurfacePolicy(_EXTRACTION, "employer", note="E4", ignore_fields=_EXTRACTION_IGNORE),
    "routers.employer_claims::employer_rbp_calculate": SurfacePolicy(_NARRATIVE, "employer", note="E5"),
    "routers.employer_pharmacy::employer_pharmacy_analyze": SurfacePolicy(_EXTRACTION, "employer", note="E6", ignore_fields=_EXTRACTION_IGNORE),
    "routers.employer_scorecard::employer_scorecard": SurfacePolicy(_EXTRACTION, "employer", note="E7 SBC + action plan", ignore_fields=_EXTRACTION_IGNORE),
    "routers.employer_trends::_generate_trend_narrative": SurfacePolicy(_NARRATIVE, "employer", note="E8"),
    # ---- Broker ------------------------------------------------------------
    "routers.broker::broker_claims_upload": SurfacePolicy(_NARRATIVE, "broker", note="K1"),
    "routers.broker::broker_scorecard_upload": SurfacePolicy(_EXTRACTION, "broker", note="K2", ignore_fields=_EXTRACTION_IGNORE),
    "routers.broker::generate_caa_letter": SurfacePolicy(
        {L: G, I: W, N: G, F: G, C: W}, "broker", fields=("letter",),
        note="K3; allow-list empty until verify.law has a USC adapter; checked on the response so the template is gated too", wired=True),
    # ---- Health ------------------------------------------------------------
    "routers.health_analyze::analyze_text": SurfacePolicy(_EXTRACTION, "health", note="H1", ignore_fields=_EXTRACTION_IGNORE),
    "routers.health_analyze::analyze_image": SurfacePolicy(_EXTRACTION, "health", note="H1 image -> UNCHECKED", ignore_fields=_EXTRACTION_IGNORE),
    "routers.ai_parse::parse_with_ai": SurfacePolicy(_EXTRACTION, "health", note="H1", ignore_fields=_EXTRACTION_IGNORE),
    "routers.eob_parse::parse_eob": SurfacePolicy(_EXTRACTION, "health", note="H1", ignore_fields=_EXTRACTION_IGNORE),
    "routers.eob_parse::parse_eob_text": SurfacePolicy(_EXTRACTION, "health", note="H1", ignore_fields=_EXTRACTION_IGNORE),
    "routers.health_analyze::analyze_sbc": SurfacePolicy(_EXTRACTION, "health", note="H2", ignore_fields=_EXTRACTION_IGNORE),
    "routers.health_analyze::analyze_denial": SurfacePolicy({L: G, I: G, N: G, F: G, C: X}, "health", note="H3: every verbatim field binds to the denial text"),
    "routers.health_analyze::_generate_appeal_result": SurfacePolicy(
        {L: G, I: W, N: G, F: G, C: W}, "health", fields=("letter_text",),
        strict_identifier_kinds=frozenset({"doi", "pmid", "pmcid", "nct", "fda_pma", "journal_cite", "bare_pmid", "et_al"}),
        note="H4: identifiers withheld (PH-4a.3); LEGAL gated with an empty allow-list; needs_revision withholds the PDF", wired=True),
    "routers.health_analyze::classify_document": SurfacePolicy(_MAPPING, "health", note="H5 exempt: document type only"),
    "routers.health_analyze::classify_text": SurfacePolicy(_MAPPING, "health", note="H5 exempt"),
    # ---- Signal (live) -----------------------------------------------------
    "routers.signal_qa::ask_question": SurfacePolicy({L: W, I: G, N: G, F: G, C: X}, "signal", note="S1: binds to the context handed over", wired=True),
    "routers.signal_metrics::generate_plain_summary": SurfacePolicy({L: W, I: G, N: G, F: G, C: X}, "signal", note="S2"),
    "routers.signal_topic_request::_parse_topic_request": SurfacePolicy(_MAPPING, "signal", note="S3 exempt: title/slug"),
    # ---- Signal (pipeline scripts -> draft rows; verify.publish gates publication) ----
    "scripts.signal.00_discover_sources::discover_sources": SurfacePolicy({L: X, I: W, N: X, F: X, C: X}, "signal", note="S4: the model proposes title/author/container/year; identifiers come only from verify.search (registry) and a proposal that resolves to nothing is marked UNRESOLVED, never guessed (2026-09-15)", wired=True),
    "scripts.signal.00_discover_sources::discover_categories": SurfacePolicy(_MAPPING, "signal", note="S4 categories"),
    "scripts.signal.extract_claims::extract_from_source": SurfacePolicy({L: X, I: G, N: X, F: G, C: X}, "signal", note="S5: gated at publish (FIGURE vs fetched text)"),
    "scripts.signal.extract_claims::deduplicate_category": SurfacePolicy(_MAPPING, "signal", note="S5 dedupe"),
    "scripts.signal.classify_claims::classify_batch": SurfacePolicy(_MAPPING, "signal", note="S5 labels"),
    "scripts.signal.score_claims::score_batch": SurfacePolicy(_MAPPING, "signal", note="S5 scores"),
    "scripts.signal.score_claims::generate_summaries": SurfacePolicy(_PROSE, "signal", note="S5 summaries: NOT covered by publish", word_figures="flag", wired=True),
    "scripts.signal.map_consensus::map_category": SurfacePolicy(_PROSE, "signal", note="S5 consensus prose: NOT covered by publish", word_figures="flag", wired=True),
    "scripts.signal.generate_summary::generate_narrative": SurfacePolicy(_PROSE, "signal", note="S5 narrative", word_figures="flag", wired=True),
    "scripts.signal.generate_summary::generate_glossary": SurfacePolicy(_PROSE, "signal", note="S5 glossary", word_figures="flag", wired=True),
    "scripts.signal.generate_notifications::generate_notification_text": SurfacePolicy({L: W, I: G, N: G, F: G, C: X}, "signal", note="S6 subscriber email"),
    "scripts.signal.golden_set::verify": SurfacePolicy(_MAPPING, "signal", note="S7 tooling"),
    # ---- WHU (observed, never gated: plan of record) -------------------------
    "scripts.signal.factcheck_draft::extract_claims": SurfacePolicy(_MAPPING, "whu", note="WHU checker role; out of scope"),
    "scripts.signal.factcheck_draft::audit_sources": SurfacePolicy(_MAPPING, "whu", note="WHU checker role; out of scope"),
    "scripts.signal.factcheck_draft::sweep_recency": SurfacePolicy(_MAPPING, "whu", note="WHU checker role; out of scope"),
    "scripts.signal.factcheck_draft::advocate": SurfacePolicy(_MAPPING, "whu", note="WHU checker role; out of scope"),
    "scripts.signal.factcheck_draft::inference": SurfacePolicy(_MAPPING, "whu", note="WHU checker role; out of scope"),
    "scripts.signal.factcheck_draft::coverage": SurfacePolicy(_MAPPING, "whu", note="WHU checker role; out of scope"),
}

# Generic wrappers: they contain the SDK call but are not surfaces. A function
# that calls one of these IS a surface. Adding a wrapper here is a policy
# decision -- test_policy_discovery fails on an anthropic import anywhere else.
WRAPPERS = {
    "routers.provider_shared::_call_claude",
    "routers.provider_shared::_call_claude_text",
    "routers.employer_shared::_call_claude",
    "routers.employer_claims::_generate_narrative",
    "routers.employer_claims::_parse_contract_pdf",     # direct SDK call; its only caller is the E4 surface
    "routers.health_analyze::_call_claude",
    "scripts.signal.00_discover_sources::_call_claude",
    "scripts.signal.classify_claims::_call_claude",
    "scripts.signal.extract_claims::_call_claude",
    "scripts.signal.generate_notifications::_call_claude",
    "scripts.signal.generate_summary::_call_claude",
    "scripts.signal.map_consensus::_call_claude",
    "scripts.signal.score_claims::_call_claude",
    "scripts.signal.factcheck_draft::call",
}

# Functions whose `.messages.create` is NOT the Anthropic SDK. Each entry is
# checked by the discovery test against the source (the named token must
# appear in the function) so the exclusion cannot rot.
NOT_A_MODEL = {
    "routers.auth::_send_sms_otp": "Twilio",
}

# Modules allowed to `import anthropic`. The goal is for this set to shrink to
# the wrappers; any module not listed that imports anthropic fails the build.
APPROVED_ANTHROPIC_IMPORTERS = {
    "routers.provider_shared", "routers.employer_shared", "routers.employer_claims",
    "routers.health_analyze", "routers.eob_parse", "routers.ai_parse",
    "routers.signal_qa", "routers.signal_metrics", "routers.signal_topic_request",
    "scripts.signal.00_discover_sources", "scripts.signal.classify_claims", "scripts.signal.extract_claims",
    "scripts.signal.generate_notifications", "scripts.signal.generate_summary", "scripts.signal.map_consensus",
    "scripts.signal.score_claims", "scripts.signal.factcheck_draft",
}


def held_for_prompt(system_prompt: str | None = None, inputs: dict | None = None, *, documents: list | None = None,
                    identifiers: set | None = None, named_ok: set | None = None, tables: dict | None = None) -> Held:
    """Held material for a surface whose model output must bind to what the
    prompt and the prompt data contained. The system prompt is included as a
    TYPED document: anything hardcoded in it is thereby permitted at this
    boundary, and is reviewed instead by the string-literal lint
    (verify/lint_literals.py), which is where a hardcoded citation is caught."""
    docs = list(documents or [])
    if system_prompt:
        docs.append(Document(Identifier("url", "system_prompt", provenance=Provenance.TYPED), "", system_prompt, kind="record"))
    return Held(documents=docs, inputs=dict(inputs or {}), identifiers=set(identifiers or ()),
                named_ok=set(named_ok or ()), tables=dict(tables or {}))


def unwired_gates() -> list[str]:
    return sorted(k for k, p in POLICY.items() if not p.wired and any(t is Tier.GATE for t in p.tiers.values()))


# ---------------------------------------------------------------------------
# Extraction surfaces: the source document as held material, and the pruning
# rule for what did not bind.
# ---------------------------------------------------------------------------
def source_document(*, text: str | None = None, pdf_bytes: bytes | None = None, image: bool = False,
                    label: str = "upload") -> Document:
    """The uploaded source as a Document. Text is DECLARED_SOUND; a PDF is
    DECLARED_SOUND only if pdftotext yields a text layer; an image, or a PDF
    with no text layer or no pdftotext on the host, is UNEXTRACTED -- every
    figure read from it is then UNCHECKED, never a pass."""
    ident = Identifier("url", label, provenance=Provenance.RESOLVED_FROM_HELD)
    if text is not None:
        return Document(ident, "", text, kind="record", text_layer="DECLARED_SOUND")
    if pdf_bytes is not None and not image:
        from .law import _pdftotext
        try:
            layer = _pdftotext(pdf_bytes)
        except Exception:
            layer = None
        if layer and layer.strip():
            return Document(ident, "", layer, kind="full_text", text_layer="DECLARED_SOUND")
        return Document(ident, "", "", kind="full_text", text_layer="UNEXTRACTED")
    return Document(ident, "", "", kind="full_text", text_layer="UNEXTRACTED")


def gate_extraction(surface: str, result: dict, held: Held, *, rows_key: str = "rates") -> dict:
    """Apply the verdict to an extraction result IN PLACE and return it:
    rows carrying a REFUSED figure are removed (they are not in the source),
    UNCHECKED rows stay and are listed, and result["verification"] carries
    Verdict.to_dict() so the API response and the stored record both say what
    was and was not checked."""
    rows = result.get(rows_key) if isinstance(result, dict) else None
    verdict = check(surface, {rows_key: rows} if rows is not None else result, held)
    if rows is not None and verdict.refusals:
        refused_paths = {f.field for f in verdict.refusals}
        keep = []
        for i, row in enumerate(rows):
            prefix = f"{rows_key}[{i}]"
            if any(p == prefix or p.startswith(prefix + ".") for p in refused_paths):
                continue
            keep.append(row)
        result[rows_key] = keep
        result["rows_removed_not_in_source"] = len(rows) - len(keep)
    result["verification"] = verdict.to_dict()
    return result
