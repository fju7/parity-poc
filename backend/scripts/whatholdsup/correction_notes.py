"""The page note on every claim bound to a source whose correction we could not read (advisor's ruling 5 on the
design review of 2026-11-26).

An unreadable CORRECTION (a linked erratum whose text cannot be held, or whose text does not name the source) no
longer blocks a source whose own text is held: the source stays held, sources.json records `correction_unreadable`
on it, and every page claim bound to it -- its own binding or an `also_rests_on` one -- carries NOTE, rendered by
orch/page.Page.render right after the claim as <span class="whu-claim-note" data-note="correction-unread">. The span
is furniture: source_ledger.plain drops it, so no sentence check reads it as a claim. An unreadable RETRACTION or
EXPRESSION OF CONCERN still refuses the source (orchestrator.code_acquire; unchanged).

The preflight row "unread corrections noted on the page" STOPs if any such claim lacks the note.
"""
from __future__ import annotations

import html as H
import json
import re
from pathlib import Path

NOTE = "This source was corrected; we could not read the correction."
KIND = "correction-unread"
SPAN = '<span class="whu-claim-note" data-note="%s">%s</span>' % (KIND, H.escape(NOTE, quote=False))
SPAN_RE = re.compile(r'<span class="whu-claim-note"[^>]*>.*?</span>', re.S)
ROW = "unread corrections noted on the page"


def norm(s: str) -> str:
    return " ".join((s or "").split())


def unread(sources_doc: dict) -> dict:
    """{source id: why} for every HELD source whose correction could not be read."""
    out = {}
    for s in (sources_doc or {}).get("sources") or []:
        cu = s.get("correction_unreadable")
        if cu and (s.get("access") or {}).get("state") == "full_text_held":
            out[s["id"]] = "%s: %s" % (cu.get("line"), cu.get("why"))
    return out


def _bound_sources(row: dict) -> set:
    ids = {row.get("source_id")} | {x.get("source_id") for x in row.get("also_rests_on") or []}
    return {i for i in ids if i}


def noted_sentences(case: Path, page_doc: dict | None = None) -> dict:
    """{normalised sentence: NOTE} for every claim bound to a source in unread(): from bindings.json's on-page rows
    and, before the bind step, from the page's own provenance (sentence -> passages)."""
    case = Path(case)
    try:
        srcs = json.loads((case / "sources.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    bad = set(unread(srcs))
    if not bad:
        return {}
    out = {}
    try:
        rows = json.loads((case / "bindings.json").read_text(encoding="utf-8")).get("bindings") or {}
    except (OSError, ValueError):
        rows = {}
    for row in rows.values():
        # A readers'-list line (origin declaration_line) says the page does NOT rely on the finding it quotes, so it
        # is not a claim bound to the source and carries no note (and the note could not be placed in that list;
        # found by the replay gate after P143, 02za).
        if row.get("origin") == "declaration_line":
            continue
        if row.get("on_page", True) and _bound_sources(row) & bad and norm(row.get("sentence")):
            out[norm(row["sentence"])] = NOTE
    for sentence, passages in ((page_doc or {}).get("provenance") or {}).items():
        if {p.get("source") for p in passages or []} & bad and norm(sentence):
            out[norm(sentence)] = NOTE
    return out


def missing_notes(case: Path, page_html: str) -> list[str]:
    """Claims bound to an unread-correction source that do not carry the note right after them on the page."""
    want = noted_sentences(case, _page_doc(case))
    if not want:
        return []
    text = page_html or ""
    miss = []
    for s in sorted(want):
        esc = H.escape(s, quote=False)
        if esc not in text and s not in text:
            continue                               # not on the page (removed): nothing to note
        if (esc + " " + SPAN) not in text and (s + " " + SPAN) not in text:
            miss.append(s)
    return miss


def _page_doc(case: Path) -> dict:
    for p in (Path(case) / "draft").glob("page.json"):
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
    return {}


def preflight_rows(slug: str, page, OK: str, BAD: str) -> list[tuple[str, str, str]]:
    """PAGE: the page's path (publish.py passes it), or its HTML."""
    import source_store as store
    if isinstance(page, Path) or (isinstance(page, str) and "<" not in page and Path(page).exists()):
        page_html = Path(page).read_text(encoding="utf-8") if Path(page).exists() else ""
    else:
        page_html = page or ""
    case = store.case_dir(slug)
    if case is None:
        return []
    try:
        srcs = json.loads((Path(case) / "sources.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    bad = unread(srcs)
    if not bad:
        return [(ROW, OK, "no held source has a correction we could not read")]
    miss = missing_notes(case, page_html)
    if miss:
        return [(ROW, BAD, "%d claim(s) bound to a source whose correction we could not read (%s) do not carry the "
                           "note %r: %s" % (len(miss), ", ".join(sorted(bad)), NOTE, " || ".join(m[:120] for m in miss[:4])))]
    return [(ROW, OK, "every claim bound to %s carries the note %r" % (", ".join(sorted(bad)), NOTE))]
