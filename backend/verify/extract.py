"""Per-class extractors: find every candidate assertion of a class in free text.

Shared assertion policy, Phase B (docs/shared-assertion-policy-phase-a-inventory.md
§D). Each extractor is a pure function text -> list[Candidate]. It finds; it
never decides. Deciding is policy.check()'s job, through the binders in this
package. Nothing here calls a model or the network.

Five classes:
  LEGAL_PROVISION   statute / code / CFR / USC / rule / manual section numbers
                    -- utils.citation_gate.find_citations, unchanged, is the extractor
  IDENTIFIER        DOI / PMID / PMCID / NCT / FDA PMA / journal-style cite
  NAMED_SOURCE      an agency, programme, guideline body, statute NAME or a
                    regulatory-status word, without a number -- the register in
                    which Health's appeal_rights relabelling happened
  FIGURE            numbers (digits or words) -- verify.numbers
  CODED_DESCRIPTOR  a code we hold (CPT/HCPCS/CARC/RARC/ICD-10/NDC) followed by a
                    descriptor the model supplied

False positives are cheap (a finding a human dismisses in seconds); false
negatives are the 2026-09-14 failures. The patterns lean wide.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from utils.citation_gate import find_citations
from .numbers import stated_figures, figures as _figures, _canon


class AssertionClass(str, Enum):
    LEGAL_PROVISION = "legal_provision"
    IDENTIFIER = "identifier"
    NAMED_SOURCE = "named_source"
    FIGURE = "figure"
    CODED_DESCRIPTOR = "coded_descriptor"


@dataclass(frozen=True)
class Candidate:
    cls: AssertionClass
    text: str            # what was found, as it appeared
    start: int
    end: int
    kind: str = ""       # sub-kind: citation family, identifier system, lexicon term, code system
    value: str = ""      # normalised value where one exists (identifier, code, figure)
    extra: str = ""      # descriptor text for CODED_DESCRIPTOR


# ---------------------------------------------------------------------------
# IDENTIFIER
# ---------------------------------------------------------------------------
_ID_PATTERNS = {
    "doi":     re.compile(r"\b10\.\d{4,9}/[^\s\"'<>)\]]+"),
    "nct":     re.compile(r"\bNCT\d{8}\b"),
    "pmcid":   re.compile(r"\bPMC\d{6,9}\b"),
    "pmid":    re.compile(r"\bPMID:?\s*\d{6,9}\b|\bpubmed\.ncbi\.nlm\.nih\.gov/\d+"),
    # a bare 7-8 digit number is the shape of a PMID typed from memory (Health's
    # _FAB_BARE_PMID_RE); it is reported as "bare_pmid" so a policy can treat
    # it as a weaker signal than an explicit PMID
    "bare_pmid": re.compile(r"(?<![\d.$,/-])\d{7,8}(?![\d.,%-])"),
    "fda_pma": re.compile(r"\b[PK]\d{6}\b"),
    "journal_cite": re.compile(r"\b(?:19|20)\d{2};\s?\d+(?:\(\d+\))?:\s?\d+"),
    "et_al":   re.compile(r"\bet al\b\.?", re.I),
}


def extract_identifiers(text: str) -> list[Candidate]:
    out = []
    for kind, rx in _ID_PATTERNS.items():
        for m in rx.finditer(text or ""):
            raw = m.group(0)
            val = raw
            if kind == "doi":
                val = raw.rstrip(".,;)").lower()
            elif kind == "pmid":
                val = re.sub(r"\D", "", raw)
            out.append(Candidate(AssertionClass.IDENTIFIER, raw, m.start(), m.end(), kind, val))
    return _dedupe(out)


# ---------------------------------------------------------------------------
# NAMED_SOURCE -- a lexicon, reviewed, small. Grows like the candidate table.
# ---------------------------------------------------------------------------
NAMED_SOURCE_LEXICON = {
    # agencies and bodies
    "fda": r"\bFDA\b|\bFood and Drug Administration\b",
    "cms": r"\bCMS\b|\bCenters for Medicare (?:&|and) Medicaid Services\b",
    "dol": r"\bDOL\b|\bDepartment of Labor\b",
    "ebsa": r"\bEBSA\b|\bEmployee Benefits Security Administration\b",
    "hhs": r"\bHHS\b|\bDepartment of Health and Human Services\b",
    "irs": r"\bIRS\b|\bInternal Revenue Service\b",
    "doi_state": r"\bDepartment of Insurance\b|\bInsurance Commissioner\b",
    "oig": r"\bOIG\b|\bOffice of Inspector General\b",
    "medicare": r"\bMedicare\b",
    "medicaid": r"\bMedicaid\b",
    # guideline bodies
    "nccn": r"\bNCCN\b|\bNational Comprehensive Cancer Network\b",
    "asco": r"\bASCO\b|\bAmerican Society of Clinical Oncology\b",
    "esmo": r"\bESMO\b",
    "nice": r"\bNICE\b|\bNational Institute for Health and Care Excellence\b",
    "uspstf": r"\bUSPSTF\b",
    "aha_acc": r"\bAHA/ACC\b|\bAmerican Heart Association\b|\bAmerican College of Cardiology\b",
    "ama": r"\bAMA\b|\bAmerican Medical Association\b",
    "who": r"\bWHO\b|\bWorld Health Organization\b",
    "cdc": r"\bCDC\b|\bCenters for Disease Control\b",
    # statute and programme names (without numbers)
    "erisa": r"\bERISA\b|\bEmployee Retirement Income Security Act\b",
    "aca": r"\bACA\b|\bAffordable Care Act\b",
    "caa": r"\bCAA\b|\bConsolidated Appropriations Act\b",
    "nsa": r"\bNo Surprises Act\b",
    "hipaa": r"\bHIPAA\b",
    "mhpaea": r"\bMHPAEA\b|\bMental Health Parity\b",
    "cobra": r"\bCOBRA\b",
    "ncci": r"\bNCCI\b|\bNational Correct Coding Initiative\b",
    "fab": r"\bField Assistance Bulletin\b",
    "advisory_opinion": r"\bAdvisory Opinion\b",
    "lcd_ncd": r"\b(?:LCD|NCD)s?\b|\bLocal Coverage Determination\b|\bNational Coverage Determination\b",
    "moldx": r"\bMolDX\b",
    # regulatory status words -- assertions about what a body has done
    "breakthrough": r"\bBreakthrough (?:Device|Therapy)\b",
    "priority_review": r"\bPriority Review\b",
    "fda_status": r"\bFDA[- ](?:approved|cleared|authori[sz]ed|designated)\b",
    "guideline_status": r"\bguideline[- ](?:recommended|endorsed|concordant)\b|\brecommended by\b|\bendorsed by\b",
    "external_review": r"\b(?:independent )?external review\b|\bindependent review organi[sz]ation\b",
}
_NAMED_RX = {k: re.compile(v, re.I if k in ("fda_status", "guideline_status", "external_review") else 0)
             for k, v in NAMED_SOURCE_LEXICON.items()}


def extract_named_sources(text: str) -> list[Candidate]:
    out = []
    for term, rx in _NAMED_RX.items():
        for m in rx.finditer(text or ""):
            out.append(Candidate(AssertionClass.NAMED_SOURCE, m.group(0), m.start(), m.end(), term, term))
    return _dedupe(out)


# ---------------------------------------------------------------------------
# LEGAL_PROVISION -- the citation gate, unchanged
# ---------------------------------------------------------------------------
def extract_legal(text: str) -> list[Candidate]:
    return [Candidate(AssertionClass.LEGAL_PROVISION, c.text, c.start, c.end, c.family, c.text)
            for c in find_citations(text or "")]


# ---------------------------------------------------------------------------
# FIGURE
# ---------------------------------------------------------------------------
def extract_figures(text: str) -> list[Candidate]:
    """Digit-form figures with position; word-form figures are folded in
    without position (verify.numbers keeps exact matching for them)."""
    out = []
    seen = set()
    cursor = 0
    for f in stated_figures(text or ""):
        raw = f.get("text") or str(f.get("value"))
        val = _canon(f["value"])
        pos = (text or "").find(raw, cursor)
        if pos < 0:
            pos = (text or "").find(raw)
        start, end = (pos, pos + len(raw)) if pos >= 0 else (0, 0)
        cursor = max(cursor, end)
        out.append(Candidate(AssertionClass.FIGURE, raw, start, end, "digits", val))
        seen.add(val)
    for v in _figures(text or ""):
        if v not in seen:
            out.append(Candidate(AssertionClass.FIGURE, v, 0, 0, "words", v))
    return out


# ---------------------------------------------------------------------------
# CODED_DESCRIPTOR
# ---------------------------------------------------------------------------
_CODE_RX = re.compile(
    r"\b(?P<system>CPT|HCPCS|CARC|RARC|ICD(?:-?10)?(?:-CM)?|NDC|APC)\b\s*(?:code)?\s*[:#]?\s*"
    r"(?P<code>[A-Z]{0,2}\d{3,5}[A-Z0-9]?|[A-Z]{1,2}-\d{1,3}|[A-Z]\d{2}(?:\.\d{1,4})?|\d{4,5}-\d{3,4}-\d{1,2}|\d{11})"
    r"\s*(?:[—–:\-]|\(|,)\s*(?P<desc>[^.\n()]{4,90})",
)


# CARC/RARC codes are written bare -- "CO-16 (missing information)" -- so the
# system prefix is optional for that shape.
_CARC_RX = re.compile(r"\b(?P<code>(?:CO|PR|OA|PI|CR)-\d{1,3}|[MN]\d{2,3}|MA\d{2,3})\b\s*(?:\(|[—–:\-])\s*(?P<desc>[^.\n()]{4,90})")


def extract_coded_descriptors(text: str) -> list[Candidate]:
    out = []
    for m in _CARC_RX.finditer(text or ""):
        out.append(Candidate(AssertionClass.CODED_DESCRIPTOR, m.group(0), m.start(), m.end(),
                             "CARC", m.group("code"), m.group("desc").strip()))
    for m in _CODE_RX.finditer(text or ""):
        sysname = m.group("system").upper().replace("-", "")
        if sysname.startswith("ICD"):
            sysname = "ICD10"
        out.append(Candidate(AssertionClass.CODED_DESCRIPTOR, m.group(0), m.start(), m.end(),
                             sysname, m.group("code"), m.group("desc").strip()))
    return _dedupe(out)


# ---------------------------------------------------------------------------
EXTRACTORS = {
    AssertionClass.LEGAL_PROVISION: extract_legal,
    AssertionClass.IDENTIFIER: extract_identifiers,
    AssertionClass.NAMED_SOURCE: extract_named_sources,
    AssertionClass.FIGURE: extract_figures,
    AssertionClass.CODED_DESCRIPTOR: extract_coded_descriptors,
}


def extract(cls: AssertionClass, text: str) -> list[Candidate]:
    return EXTRACTORS[cls](text)


def _dedupe(cands: list[Candidate]) -> list[Candidate]:
    """Keep the longest match at each position (the citation gate's rule)."""
    keep = [c for c in cands if not any(o is not c and o.start <= c.start and c.end <= o.end
                                        and (o.end - o.start) > (c.end - c.start) for o in cands)]
    seen, out = set(), []
    for c in sorted(keep, key=lambda c: (c.start, -c.end, c.kind)):
        key = (c.start, c.end, c.kind)
        if key not in seen:
            seen.add(key); out.append(c)
    return out
