"""Evidence citations in a letter: VERIFIED by lookup, not blocked (APPEALS-3, 2026-09-17).

Fred's ruling: citation of clinical evidence is encouraged; citation of law is removed. The
gate therefore has two jobs on a letter -- refuse the legal register (extract.LEGAL_REGISTER)
and verify every literature identifier the letter carries:

  1. the identifier must RESOLVE at its registry (literature.resolve: Handle/Crossref for a
     DOI, Europe PMC for a PMID/PMCID, clinicaltrials.gov for an NCT) -- a fabricated one
     is a refusal; a fabricated reference discredits the whole appeal;
  2. the record's TITLE must match the citation the identifier sits in -- the same line of
     the letter (extract._citation_window), compared with text.agreement: containment of
     one normalised string in the other, or a shared distinctive-token ratio >= TITLE_MATCH
     (0.5 of the shorter side's content tokens). A resolving identifier attached to the
     wrong paper is a refusal;
  3. a registry that does not answer (HTTP 0/429/5xx, unparseable body) leaves the citation
     UNVERIFIED -- Finding.ok is None, the verdict is not `verified`, and the caller must
     not treat it as a pass. Never "no answer = fine".

Identifiers the system itself handed to the model (Held.identifiers -- the retrieved
evidence pack) are verified the same way; the pack's own resolution, when the caller
supplies it in Held.resolutions, is used instead of a second network round-trip.
Citation shapes WITHOUT a resolvable identifier (an author-year string, a bare volume:page)
stay refusals: a letter may not cite what a reader cannot look up.
"""
from __future__ import annotations

from .extract import AssertionClass, Candidate, _citation_window, extract
from .literature import resolve as _resolve
from .text import LITERATURE_BOILERPLATE, agreement
from .types import Exists, Identifier, Provenance

TITLE_MATCH = 0.5
RESOLVABLE = ("doi", "pmid", "pmcid", "nct")


def _identifier(c: Candidate) -> Identifier | None:
    if c.kind not in RESOLVABLE:
        return None
    val = c.value
    if c.kind == "pmid":
        val = "".join(ch for ch in val if ch.isdigit())
    return Identifier(c.kind, val, c.text, Provenance.TYPED)   # written by the model, from memory or from the pack


def verify_citation(c: Candidate, text: str, resolutions: dict | None = None):
    """(ok, reason, heading) for one identifier candidate. ok is True / False / None."""
    ident = _identifier(c)
    if ident is None:
        return False, "citation carries no resolvable identifier (DOI, PMID, PMCID or NCT)", None
    key = f"{ident.system}:{ident.value.lower()}"
    res = (resolutions or {}).get(key) or _resolve(ident)
    if res.exists is Exists.NONEXISTENT:
        return False, f"{ident.system.upper()} {ident.value} does not exist at {res.registry or 'its registry'}", None
    if res.exists is not Exists.EXISTS:
        why = "; ".join(f"{k}: {v}" for k, v in (res.extra.get("registry_unavailable") or {}).items()) or "registry gave no answer"
        return None, f"could not be verified: {why}", None
    if not res.heading:
        return None, f"{ident.system.upper()} {ident.value} exists but its registry returned no title to match", None
    window = _citation_window(text, c.start, c.end)
    ratio, shared = agreement(window, res.heading, LITERATURE_BOILERPLATE)
    if ratio >= TITLE_MATCH:
        return True, f"resolves at {res.registry}; title matches the citation ({ratio:.2f})", res.heading
    return False, (f"{ident.system.upper()} {ident.value} resolves to \"{res.heading[:90]}\" which does not match "
                   f"the citation it is attached to ({ratio:.2f} shared)"), res.heading


def verify_all(text: str, resolutions: dict | None = None) -> list[tuple[Candidate, bool | None, str]]:
    return [(c, *verify_citation(c, text, resolutions)[:2]) for c in extract(AssertionClass.IDENTIFIER, text)]
