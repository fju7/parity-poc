"""bind(assertion, document) — does the document contain what the assertion says?

Four kinds (design doc §4). Each is a pure function of (what the assertion
says, what the registry heading is, what the document text contains, the
context). None asserts the assertion is TRUE; R1 of the WHU bindings spec
governs: a binding says a heading agrees, a number is present, a span is
present, a rule applies. What that means is a person's to decide.
"""
from __future__ import annotations

import re

from .numbers import figures, canonical_numbers
from .text import agreement, content_tokens, normalise, LITERATURE_BOILERPLATE, LAW_BOILERPLATE, GENERIC_BOILERPLATE
from .types import Binding, Context, Document, Kind, Resolution, LAW

# Zero shared distinctive words means a different document. The threshold is
# deliberately at zero: a check that cries wolf gets switched off.
HEADING_DIFFERENT_DOCUMENT = 0.0

# HEADING ABSTAINS when there is too little to compare. Every boilerplate
# addition (oncology on 2026-09-14; cardiology and diabetes will follow)
# weakens HEADING by leaving fewer distinctive words, and nothing noticed.
# So when fewer than HEADING_MIN_DISTINCTIVE remain on either side after
# boilerplate removal, HEADING returns cannot_discriminate -- not ok -- and
# FIGURE or SPAN becomes MANDATORY for that source (see bind()).
#
# N = 2, chosen from the golden sets on 2026-09-14: the positive with the
# fewest distinctive words and no figure or quotation to fall back on is
# 45 CFR 147.200, "summary of benefits and coverage" -> {summary, benefits},
# exactly two. At N = 3 it would abstain and, with nothing mandatory to
# check, be refused: a false negative. At N = 2 every positive still binds
# and four law negatives route through abstention (headings "Rules",
# "Purpose of sections", "Coverage of preventive health services",
# "Incomplete or Invalid Claims Processing Terminology" against
# characterisations with one distinctive word). Containment -- "MONARCH 3"
# inside the registry's acronym field -- is decisive whatever the count.
HEADING_MIN_DISTINCTIVE = 2


def bind_heading(characterisation: str, resolution: Resolution) -> Binding:
    """Does our characterisation share distinctive words with the registry's heading?

    Three outcomes: ok, a refusal (zero shared), or cannot_discriminate."""
    if not resolution.heading:
        return Binding(Kind.HEADING, False, reason="registry returned no heading; cannot compare")
    bp = LAW_BOILERPLATE if resolution.identifier.registry == "law" else (LITERATURE_BOILERPLATE | GENERIC_BOILERPLATE)
    ratio, shared = agreement(characterisation, resolution.heading, bp)
    if ratio == 1.0 and shared:                      # containment: decisive
        return Binding(Kind.HEADING, True, evidence="containment: " + ", ".join(sorted(shared)))
    ours = len(content_tokens(characterisation, bp))
    theirs = max((len(content_tokens(c, bp)) for c in resolution.heading.split(" || ")), default=0)
    if min(ours, theirs) < HEADING_MIN_DISTINCTIVE:
        return Binding(Kind.HEADING, False, abstained=True, evidence=resolution.heading[:160],
                       reason=f"cannot_discriminate: {ours} distinctive word(s) on our side, "
                              f"{theirs} in the registry heading; FIGURE or SPAN is mandatory")
    if ratio <= HEADING_DIFFERENT_DOCUMENT:
        return Binding(Kind.HEADING, False, evidence=resolution.heading[:160],
                       reason="shares no distinctive word with the registry heading")
    return Binding(Kind.HEADING, True, evidence=", ".join(sorted(shared)))


def bind_figure(assertion: str, document: Document, registry_text: str = "") -> Binding:
    """Is every number the assertion commits to present in the document?

    `registry_text`: what the registry says about the document -- its title and
    publication year -- which is part of what the document IS. An abstract does
    not contain its own year; "Smeeth 2004" must not fail on that."""
    want = figures(assertion)
    if not want:
        return Binding(Kind.FIGURE, True, evidence="no figure in assertion")
    if document.text_layer != "DECLARED_SOUND":
        return Binding(Kind.FIGURE, False, reason=f"document text layer is {document.text_layer}; "
                       "absence cannot be judged")
    have = canonical_numbers(document.text) | canonical_numbers(registry_text or "")
    missing = sorted(want - have)
    if missing:
        return Binding(Kind.FIGURE, False, evidence=", ".join(sorted(want & have)),
                       reason="not in the document: " + ", ".join(missing))
    return Binding(Kind.FIGURE, True, evidence=", ".join(sorted(want)))


_QUOTE = re.compile(r"[\"“”']([^\"“”']{12,})[\"“”']")


def bind_span(assertion: str, document: Document, quoted: str | None = None) -> Binding:
    """Is the quoted passage in the document verbatim (whitespace/case/typography-insensitive)?"""
    spans = [quoted] if quoted else [m.group(1) for m in _QUOTE.finditer(assertion)]
    if not spans:
        return Binding(Kind.SPAN, True, evidence="no quotation in assertion")
    if document.text_layer != "DECLARED_SOUND":
        return Binding(Kind.SPAN, False, reason=f"document text layer is {document.text_layer}")
    hay = normalise(document.text)
    for s in spans:
        if normalise(s) not in hay:
            return Binding(Kind.SPAN, False, reason=f"not in the document: {s[:80]!r}")
    return Binding(Kind.SPAN, True, evidence=f"{len(spans)} span(s) present")


# APPLICABILITY: a rule table, not a lookup. Small on purpose.
MEDICARE_ONLY_CFR = range(400, 499)           # 42 CFR parts 400-498
MEDICARE_ONLY_SYSTEMS = {"cms_iom", "ncci"}
SCOPE_EXCLUSIONS = {                          # heading words that name a domain other than health
    "health": {"property", "casualty", "workers", "fidelity", "surety", "suretyship", "boiler",
               "title", "annuity", "annuities", "life", "automobile", "motor", "marine", "crop"},
}


def bind_applicability(resolution: Resolution, context: Context) -> Binding:
    ident = resolution.identifier
    if ident.registry != "law":
        return Binding(Kind.APPLICABILITY, True, evidence="not a law citation")
    # Medicare-only sources bind only to a Medicare/Medicaid payer.
    medicare_only = ident.system in MEDICARE_ONLY_SYSTEMS
    if ident.system == "cfr":
        m = re.match(r"^42:(\d+)\.", ident.value)
        if m and int(m.group(1)) in MEDICARE_ONLY_CFR:
            medicare_only = True
    if medicare_only and context.payer_type not in ("medicare", "medicaid"):
        return Binding(Kind.APPLICABILITY, False,
                       reason=f"a Medicare rule cited against a {context.payer_type} payer")
    # A state code binds only to the practice's state.
    if ident.system in ("orc", "oac") and context.state and context.state != "OH":
        return Binding(Kind.APPLICABILITY, False,
                       reason=f"an Ohio provision cited for a practice in {context.state}")
    # A provision whose heading names another domain does not bind to this claim.
    heading_words = set(normalise(resolution.heading or "").split())
    excl = SCOPE_EXCLUSIONS.get(context.claim_domain, set()) & heading_words
    if excl:
        return Binding(Kind.APPLICABILITY, False, evidence=resolution.heading or "",
                       reason=f"heading names a different domain: {', '.join(sorted(excl))}")
    return Binding(Kind.APPLICABILITY, True)


def bind(assertion: str, resolution: Resolution, document: Document | None,
         context: Context = Context(), quoted: str | None = None,
         characterisation: str | None = None) -> list[Binding]:
    """Every kind that applies, in order. `characterisation` defaults to the assertion."""
    head = bind_heading(characterisation or assertion, resolution)
    out = [head]
    if resolution.identifier.registry == "law":
        out.append(bind_applicability(resolution, context))
    has_figure = bool(figures(assertion))
    has_quote = bool(quoted or _QUOTE.search(assertion))
    if has_figure:
        out.append(bind_figure(assertion, document) if document else
                   Binding(Kind.FIGURE, False, reason="no document fetched; a figure cannot be checked"))
    if has_quote:
        out.append(bind_span(assertion, document, quoted) if document else
                   Binding(Kind.SPAN, False, reason="no document fetched; a span cannot be checked"))
    if head.abstained and not (has_figure or has_quote):
        # Abstention converts HEADING's weakness into a statement: with nothing
        # mandatory to check, this source cannot be bound at all.
        out[0] = Binding(Kind.HEADING, False, abstained=True, evidence=head.evidence,
                         reason=head.reason + "; the assertion carries neither, so it cannot be bound")
    return out


def bind_all(*args, **kwargs) -> tuple[bool, list[Binding]]:
    """(ok, bindings). ok when every kind that applies is ok, EXCEPT that an
    abstaining HEADING is satisfied by a passing mandatory FIGURE or SPAN."""
    bs = bind(*args, **kwargs)
    head = bs[0]
    others = bs[1:]
    if head.abstained:
        mandatory = [b for b in others if b.kind in (Kind.FIGURE, Kind.SPAN)]
        return bool(mandatory) and all(b.ok for b in others), bs
    return all(b.ok for b in bs), bs
