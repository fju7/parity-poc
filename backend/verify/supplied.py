"""Provenance.OPERATOR_SUPPLIED: a document a person fetched by hand enters the
corpus without weakening anything.

WHY. Five documents mmr-vaccine-autism needs cannot be got by machine -- the
Lancet retraction notice (Elsevier serves a shell), Deer's BMJ investigation
(403), the Cedillo decision (moved), FDA BLA 103166 (404), the GMC
determination (no URL on file). Between them they withhold a dozen or more
claims. A person with a browser can get several. Until now the only way that
file could become evidence was to paste its text in, which is the content_text
defect with a person in the model's chair.

THE RULE, and it is the whole design: THE OPERATOR SUPPLIES THE DOCUMENT,
NEVER THE CONCLUSION. Nothing in this module lets a person assert that a
source supports a claim.

    input        the file; the URL it was fetched from; who supplied it;
                 the identifier it is offered for
    the record   sha256 of the bytes, retrieved_at, supplied_by, source URL,
                 Provenance.OPERATOR_SUPPLIED -- distinguishable from a
                 machine fetch in every downstream record
    HEADING      MANDATORY and may not abstain. The registry says what the
                 document for this identifier IS; the supplied file's own
                 title has to match it. A mismatch refuses the file and
                 nothing enters. This is the check that stops a wrong PDF
                 becoming a right citation. A registry that does not answer
                 also refuses: without its title there is nothing to check
                 the file against.
    bind         otherwise UNCHANGED. FIGURE, SPAN, CHRONOLOGY run against
                 the supplied text at publish exactly as against a machine
                 fetch. A hand-fetched document that does not support the
                 claim still withholds it.
    PDFs         a text layer is extracted and whether one existed is
                 recorded. A scanned image with no text layer is UNCHECKED,
                 never a pass -- the rule for a rate read from an image.

Admitted documents live content-addressed beside the machine-fetched ones
(data/verify/docs/<sha2>/<sha>.txt.gz) and are indexed by identifier in
data/verify/supplied/index.json, each with its supply record. publish.gate_source
uses one only when the machine route got nothing, and says so on the record.
Every admission is a post-freeze change: docs/signal-corpus-freeze.md gets a
row (hash, URL, who, which claims moved).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import generic, literature
from .bind import bind_heading
from .text import agreement, content_tokens, LITERATURE_BOILERPLATE
from .types import Binding, Document, Exists, Identifier, Kind, Provenance, Resolution

BACKEND = Path(__file__).resolve().parent.parent
SUPPLIED = BACKEND / "data" / "verify" / "supplied"
INDEX = SUPPLIED / "index.json"
_NOW = lambda: dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()  # noqa: E731

# The registry's title must match the supplied document's OWN TITLE LINES
# (the first lines of a PDF, <title>/<h1>/citation_title of a page) at this
# ratio with this many words shared, or be contained WHOLE in the first
# HEAD_CHARS of the text. Only the short title lines get the ratio rule: a
# same-topic abstract shares most of a title's words ("measles, mumps,
# rubella, vaccination, autism, cohort"), and on 2026-09-15 a 4,000-character
# head let Madsen 2002 pass as Hviid 2019 at 0.86. Stricter than
# bind_heading (0.6 / 3 on a machine fetch): a pass here ADMITS bytes a
# person chose.
HEAD_CHARS = 400
TITLE_RATIO = 0.8
TITLE_MIN = 4


@dataclass
class Supply:
    admitted: bool
    status: str                       # ADMITTED | REFUSED_HEADING | REFUSED_REGISTRY | REFUSED_NONEXISTENT | UNCHECKED_NO_TEXT_LAYER
    reason: str
    sha256: str
    identifier: Identifier | None
    resolution: Resolution | None
    document: Document | None
    heading: Binding | None
    record: dict = field(default_factory=dict)


# A title sits in the first few lines, is short, and is not a sentence. The
# candidates are the short lines among the first TITLE_LINES that contain no
# sentence boundary (". "), singly and joined with the next such line, since
# a title wraps ("Retraction—Ileal-lymphoid-nodular hyperplasia, non-specific
# colitis," / "and pervasive developmental disorder in children") and a
# browser print puts page chrome above it. An abstract line is a sentence
# and never a candidate: joined to its neighbour it would carry "measles,
# mumps, rubella, vaccination, autism, cohort" and admit Madsen 2002 as
# Hviid 2019.
TITLE_LINES = 8
TITLE_LINE_MAX = 200


def _title_lines(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()][:TITLE_LINES]
    ok = [ln if (len(ln) <= TITLE_LINE_MAX and ". " not in ln) else None for ln in lines]
    out = [ln for ln in ok if ln]
    for a, b in zip(ok, ok[1:]):
        if a and b and not a.rstrip().endswith((".", "?", "!")):
            out.append(a + " " + b)
    return out


def _text_layer(data: bytes, content_type: str) -> tuple[str, str, list[str]]:
    """(text, text_layer, candidate titles) from the bytes. A PDF with no
    extractable text is UNEXTRACTED."""
    if data.startswith(b"%PDF") or content_type == "application/pdf":
        from .law import _pdftotext
        text = _pdftotext(data)
        if text is None:
            return "", "UNEXTRACTED", []          # no pdftotext on this machine: cannot judge
        if len(" ".join(text.split())) < 40:
            return "", "UNEXTRACTED", []          # a scanned image: no text layer
        return " ".join(text.split()), "DECLARED_SOUND", _title_lines(text)
    page = data.decode("utf-8", "replace")
    if re.search(r"<(html|body|title|h1)\b", page, re.I):
        return generic._strip(page), "DECLARED_SOUND", generic._titles(page)
    return " ".join(page.split()), "DECLARED_SOUND", _title_lines(page)


# A document that prints its own DOI in its head must print the one it is
# offered for, FIRST. BMJ's correction notice d1678 carries the SAME title as
# the editorial it corrects (c7452), so a title check alone admits it as the
# editorial (2026-09-15); its head says "doi: 10.1136/bmj.d1678" and then,
# under "See original article", c7452.
SELF_ID_CHARS = 1500


def _self_identifier_agrees(ident: Identifier, text: str) -> Binding | None:
    """A refusal when the FIRST identifier of our system in the document's
    head is not ours; None when it is, or when the head names none. The
    first is the document's own: a correction notice prints its own DOI and
    then, lower, the DOI of the article it corrects, so "ours is somewhere
    in the head" would still admit d1678 as c7452."""
    from .extract import AssertionClass, extract
    head = text[:SELF_ID_CHARS]
    found = [c.value.lower().rstrip(".,;)") for c in sorted(extract(AssertionClass.IDENTIFIER, head), key=lambda c: c.start)
             if c.kind == ident.system]
    if found and found[0] != ident.value.lower():
        return Binding(Kind.HEADING, False, evidence=", ".join(found),
                       reason=f"the supplied document names a different {ident.system.upper()} as its own: {found[0]}; offered as {ident.value}")
    return None


def _registry_title_in_document(registry_heading: str, titles: list[str], text: str) -> Binding:
    """HEADING for a supplied file: the registry's title against the file's own
    title lines and the head of its text. Never abstains."""
    heads = [h for h in (registry_heading or "").split(" || ") if h]
    if not heads:
        return Binding(Kind.HEADING, False, reason="registry returned no heading; a supplied file cannot be checked against nothing")
    theirs = min(len(content_tokens(h, LITERATURE_BOILERPLATE)) for h in heads)
    best = (0.0, set(), "")
    for h in heads:
        for cand in titles:                                   # the document's own title lines: ratio rule
            ratio, shared = agreement(h, cand, LITERATURE_BOILERPLATE)
            if (ratio, len(shared)) > (best[0], len(best[1])):
                best = (ratio, shared, cand[:120])
            if ratio >= TITLE_RATIO and len(shared) >= TITLE_MIN:
                return Binding(Kind.HEADING, True, evidence=f"registry title matches the document's title line (ratio {ratio:.2f}): " + ", ".join(sorted(shared)))
        ratio, shared = agreement(h, text[:HEAD_CHARS], LITERATURE_BOILERPLATE)   # the head of the text: containment only
        if ratio == 1.0 and shared and theirs >= 2:
            return Binding(Kind.HEADING, True, evidence="registry title found whole in the head of the supplied document: " + ", ".join(sorted(shared)))
        if (ratio, len(shared)) > (best[0], len(best[1])):
            best = (ratio, shared, text[:120])
    ratio, shared, cand = best
    return Binding(Kind.HEADING, False, evidence=cand,
                   reason=f"the supplied document's title does not match the registry's title for this identifier "
                          f"(ratio {ratio:.2f}, {len(shared)} shared word(s)): registry says '{heads[0][:100]}'")


def supply(path: str | Path, source_url: str, supplied_by: str, identifier: str,
           content_type: str | None = None, store: bool = True) -> Supply:
    """Offer a hand-fetched file as the document for `identifier` (a DOI, PMID,
    PMCID or NCT). Refuses unless the registry names the identifier and the
    file carries that title. `store=False` runs every check and writes nothing."""
    data = Path(path).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    now = _NOW()
    ident0 = literature.identify(identifier)
    if ident0 is None:
        return Supply(False, "REFUSED_REGISTRY", f"'{identifier}' is not a DOI, PMID, PMCID or NCT identifier; a supplied file must be offered for an identifier a registry can answer for",
                      sha, None, None, None, None)
    ident = Identifier(ident0.system, ident0.value, identifier, Provenance.OPERATOR_SUPPLIED)
    res = literature.resolve(ident)
    base = {"sha256": sha, "retrieved_at": now, "supplied_by": supplied_by, "source_url": source_url,
            "provenance": Provenance.OPERATOR_SUPPLIED.value, "identifier": f"{ident.system}:{ident.value}",
            "registry": res.registry, "registry_heading": res.heading, "bytes": len(data)}
    if res.exists == Exists.UNCHECKED:
        why = (res.extra or {}).get("registry_unavailable") or {}
        return Supply(False, "REFUSED_REGISTRY", "registry did not answer for this identifier; the file cannot be checked against its title -- retry later: "
                      + "; ".join(f"{k}: {v}" for k, v in why.items()), sha, ident, res, None, None, base)
    if res.exists == Exists.NONEXISTENT:
        return Supply(False, "REFUSED_NONEXISTENT", "the registry holds no such identifier; a file cannot be evidence for an identifier that does not exist",
                      sha, ident, res, None, None, base)
    ctype = content_type or ("application/pdf" if data.startswith(b"%PDF") else "text/html" if b"<html" in data[:4000].lower() else "text/plain")
    text, layer, titles = _text_layer(data, ctype)
    doc = Document(ident, sha, text, ctype, now, source_url, "operator_supplied", "full_text", layer)
    if layer != "DECLARED_SOUND":
        rec = {**base, "text_layer": layer, "status": "UNCHECKED_NO_TEXT_LAYER",
               "heading": {"kind": "HEADING", "ok": None, "reason": "no text layer; the title cannot be read, so the file cannot be checked"}}
        if store:
            _store(doc, rec)
        return Supply(False, "UNCHECKED_NO_TEXT_LAYER", "the file has no text layer (a scanned image); it is recorded as supplied and UNCHECKED -- never a pass",
                      sha, ident, res, doc, None, rec)
    head = _self_identifier_agrees(ident, text) or _registry_title_in_document(res.heading or "", titles, text)
    rec = {**base, "text_layer": layer, "chars": len(text), "document_titles": titles[:3],
           "heading": {"kind": "HEADING", "ok": head.ok, "evidence": head.evidence, "reason": head.reason}}
    if not head.ok:
        rec["status"] = "REFUSED_HEADING"
        return Supply(False, "REFUSED_HEADING", head.reason, sha, ident, res, None, head, rec)
    rec["status"] = "ADMITTED"
    if store:
        rec["path"] = _store(doc, rec)
    return Supply(True, "ADMITTED", "admitted: the registry's title is in the supplied document", sha, ident, res, doc, head, rec)


def _store(doc: Document, rec: dict) -> str:
    from .publish import store_document
    path = store_document(doc)
    SUPPLIED.mkdir(parents=True, exist_ok=True)
    (SUPPLIED / f"{doc.sha256}.json").write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding="utf-8")
    idx = json.loads(INDEX.read_text()) if INDEX.exists() else {}
    key = f"{doc.identifier.system}:{doc.identifier.value}"
    if rec.get("status") == "ADMITTED":
        idx[key] = {"sha256": doc.sha256, "path": path, "record": f"data/verify/supplied/{doc.sha256}.json",
                    "supplied_by": rec["supplied_by"], "retrieved_at": rec["retrieved_at"], "source_url": rec["source_url"]}
        INDEX.write_text(json.dumps(idx, indent=1, sort_keys=True), encoding="utf-8")
    return path


def lookup(ident: Identifier) -> tuple[Document, dict] | None:
    """The admitted supplied document for an identifier, or None."""
    if not INDEX.exists():
        return None
    entry = json.loads(INDEX.read_text()).get(f"{ident.system}:{ident.value}")
    if not entry:
        return None
    import gzip
    p = BACKEND / entry["path"]
    if not p.exists():
        return None
    text = gzip.open(p, "rt", encoding="utf-8").read()
    doc = Document(Identifier(ident.system, ident.value, ident.raw, Provenance.OPERATOR_SUPPLIED), entry["sha256"], text,
                   "", entry["retrieved_at"], entry["source_url"], "operator_supplied", "full_text", "DECLARED_SOUND", str(p))
    return doc, entry
