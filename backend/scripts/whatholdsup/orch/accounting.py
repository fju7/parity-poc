"""Every sentence on the page has a record; every sentence that leaves it has one too (E7, E8, E9).

The offline replay found three drafter edits that no log records (advisor's ruling 2026-11-07, list E 7-9):
  E7  a source-list line edited by hand after the draft (Q1-02b);
  E8  two sentences carrying the audit's first-read proposed wording, which no accepted ruling chose (Q1-03b);
  E9  a sentence removed with no record (Q1-03b, after an omission ADD).

The orchestrator has no drafting agent, and the chain stops any write by a step that does not own the page. This
check closes what is left: a step that does own the page may change it only in ways a record explains. It runs
after every page-owning step (orchestrator.run_step) and the run stops on any problem.

What explains a sentence ON the page:
  - in a prose block: the sentence is a key of page.json's provenance (written by the code that put it there --
    the draft, a coverage statement, a judgement sentence) or the text an applied record produced
    (orchestrator/applied.jsonl: an accepted ruling's text, an omission ADD). A first-read proposal is neither (E8);
  - in a code-written block: the block's own generator, run now, writes it (the source list from sources.json, which
    is frozen after `acquire`, so a hand-edited source line is never explained) (E7).
What explains a sentence LEAVING the page: an applied record's old sentence, or (code-written blocks only) its
generator no longer writing it (E9).
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from orch.page import Page, norm, split
import source_ledger as ledger

APPLIED_LOG = "orchestrator/applied.jsonl"


def html_sentences(html_text: str) -> list[str]:
    out = []
    for line in (html_text or "").splitlines():
        if line.strip():
            out += [norm(s) for s in ledger.sentences(ledger.plain(line)) if norm(s)]
    return out


def applied(case: Path) -> tuple[set, set]:
    """(old sentences the applied records removed or replaced, sentences they produced)."""
    olds, news = set(), set()
    p = Path(case) / APPLIED_LOG
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("op") in ("replace", "delete") and r.get("old"):
                olds |= set(split(r["old"])) | {norm(r["old"])}
            if r.get("op") in ("replace", "insert") and r.get("new"):
                new = r["new"]
                news |= set(split(" ".join(new) if isinstance(new, list) else new))
    return olds, news


def on_page(page: Page) -> dict:
    """{"prose": [...], "<section>": [...]} -- the page's sentences by where they sit."""
    out: dict = {"prose": []}
    for b in page.blocks():
        if b.get("tag") == "p":
            out["prose"] += [norm(s) for s in b.get("sentences") or []]
        elif b.get("tag") == "html":
            out.setdefault(b.get("section") or "?", []).extend(html_sentences(b.get("html") or ""))
    return out


def problems(case: Path, page: Page, generated: dict, prev: dict | None) -> list[str]:
    """Every sentence on PAGE or gone from it since PREV that no record explains. GENERATED maps a code-written
    section to its generator's html, run now; a code-written section with no generator is not explained."""
    olds, news = applied(case)
    prov = {norm(k) for k in (page.doc.get("provenance") or {})}
    now = on_page(page)
    gen = {sec: set(html_sentences(h)) for sec, h in generated.items()}
    bad = []
    for s in now["prose"]:
        if s not in prov and s not in news:
            bad.append("E8: a sentence on the page that no record put there: %r" % s[:120])
    for sec, sents in now.items():
        if sec == "prose":
            continue
        if sec not in gen:
            bad.append("E7: a code-written block with no generator: %r" % sec)
            continue
        for s in sents:
            if s not in gen[sec]:
                bad.append("E7: a %s line its generator does not write: %r" % (sec, s[:120]))
    if prev:
        for sec, sents in prev.items():
            gone = Counter(sents) - Counter(now.get(sec) or [])
            for s in gone:
                if s in olds:
                    continue
                if sec != "prose" and s not in gen.get(sec, set()):
                    continue                    # its generator no longer writes it
                bad.append("E9: a sentence left the page with no record: %r" % s[:120])
    return bad
