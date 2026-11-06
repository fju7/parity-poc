"""The page model and the code applier (docs/whu-orchestrator.md §2.2).

An orchestrated page is kept as draft/page.json and rendered to
draft/<slug>.html by code. Every edit -- a ruling's replacement, an audit cut,
an omission ADD, a fail-safe removal -- is an operation on page.json made by
this module, never by hand and never by a model:

    replace(old_sentence, new_text)   new_text "" deletes the sentence
    delete(sentence)
    insert_after(anchor_fingerprint, text)

Sentences are matched exactly as changecheck and applied_check see them
(whitespace collapsed). An operation that cannot be placed raises NotPlaced,
which the orchestrator turns into a STOP: the applier never guesses.

Blocks: {"tag": "h2"|"h3", "text"}; {"tag": "p", "sentences": [...]} for
model-written prose; {"tag": "html", "section", "html"} for code-generated
blocks (lean_sentences render, coverage_check render, the source list), whose
<p> lines can be deleted by a removal but are never rewritten.
"""
from __future__ import annotations

import hashlib
import html as H
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import source_ledger as ledger  # noqa: E402


class NotPlaced(RuntimeError):
    pass


def norm(s: str) -> str:
    return " ".join((s or "").split())


def fingerprint(s: str) -> str:
    """bindings.fingerprint: sha256 of the whitespace-collapsed text, 16 hex."""
    return hashlib.sha256(norm(s).encode("utf-8")).hexdigest()[:16]


def split(text: str) -> list[str]:
    """A ruling's text as page sentences (applied_check.norm_sentences)."""
    return [norm(s) for s in ledger.sentences(ledger.plain(text or "")) if norm(s)]


def _plain_line(line: str) -> str:
    return norm(ledger.plain(line))


class Page:
    def __init__(self, doc: dict):
        self.doc = doc
        self.ops: list[dict] = []

    @classmethod
    def load(cls, path: Path) -> "Page":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def save(self, path: Path) -> None:
        Path(path).write_text(json.dumps(self.doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # -- reading
    def blocks(self) -> list[dict]:
        return self.doc.setdefault("blocks", [])

    def sentences(self) -> list[str]:
        out = []
        for b in self.blocks():
            if b.get("tag") == "p":
                out += [norm(s) for s in b.get("sentences") or []]
            elif b.get("tag") == "html":
                for line in (b.get("html") or "").splitlines():
                    if line.strip():
                        out += [norm(s) for s in ledger.sentences(ledger.plain(line)) if norm(s)]
        return out

    def _find(self, sentence: str):
        """(block index, sentence index or line index, kind) of the one place SENTENCE is; NotPlaced otherwise."""
        want = norm(sentence)
        hits = []
        for bi, b in enumerate(self.blocks()):
            if b.get("tag") == "p":
                for si, s in enumerate(b.get("sentences") or []):
                    if norm(s) == want:
                        hits.append((bi, si, "p"))
            elif b.get("tag") == "html":
                for li, line in enumerate((b.get("html") or "").splitlines()):
                    if want and want in [norm(x) for x in ledger.sentences(ledger.plain(line))]:
                        hits.append((bi, li, "html"))
        if len(hits) != 1:
            raise NotPlaced("%s on the page: %r" % ("not found" if not hits else "%d copies" % len(hits),
                                                     want[:120]))
        return hits[0]

    # -- operations
    def replace(self, old: str, new_text: str, why: str = "") -> None:
        bi, si, kind = self._find(old)
        new = split(new_text)
        b = self.blocks()[bi]
        if kind == "html":
            if new:
                raise NotPlaced("a code-written line is never rewritten: %r" % norm(old)[:120])
            lines = b["html"].splitlines()
            del lines[si]
            b["html"] = "\n".join(lines)
        else:
            b["sentences"][si:si + 1] = new
            if not b["sentences"]:
                del self.blocks()[bi]
        self.ops.append({"op": "replace" if new else "delete", "old": norm(old), "new": new, "why": why})

    def delete(self, sentence: str, why: str = "") -> None:
        self.replace(sentence, "", why)

    def insert_after(self, anchor_fp: str, text: str, why: str = "") -> None:
        new = split(text)
        if not new:
            raise NotPlaced("nothing to insert")
        hits = [(bi, si) for bi, b in enumerate(self.blocks()) if b.get("tag") == "p"
                for si, s in enumerate(b.get("sentences") or []) if fingerprint(s) == anchor_fp]
        if len(hits) != 1:
            raise NotPlaced("anchor %s: %s" % (anchor_fp, "not on the page" if not hits else "ambiguous"))
        bi, si = hits[0]
        # After any earlier insertion at the same anchor, so several ADDs tile in order.
        b = self.blocks()[bi]
        at = si + 1
        prior = [o for o in self.ops if o.get("op") == "insert" and o.get("anchor") == anchor_fp]
        at += sum(len(o["new"]) for o in prior)
        b["sentences"][at:at] = new
        self.ops.append({"op": "insert", "anchor": anchor_fp, "new": new, "why": why})

    def set_html(self, section: str, html_text: str) -> None:
        """Replace a code-generated block's html (re-rendered from its generator)."""
        for b in self.blocks():
            if b.get("tag") == "html" and b.get("section") == section:
                b["html"] = html_text
                return
        raise NotPlaced("no generated block %r" % section)

    # -- rendering
    def render(self) -> str:
        title = H.escape(self.doc.get("title") or "")
        out = ["<!doctype html>", '<html lang="en">', "<head>", '<meta charset="utf-8">',
               "<title>%s — What Holds Up</title>" % title, '<meta name="robots" content="noindex,nofollow">',
               "</head>", "<body>", "<header>", "<h1>%s</h1>" % title, "</header>", "<main>"]
        section = None
        for b in self.blocks():
            sec = b.get("section")
            if sec != section:
                if section is not None:
                    out.append("</section>")
                out += ["", '<section id="%s">' % H.escape(sec or "body")]
                section = sec
            tag = b.get("tag")
            if tag in ("h2", "h3"):
                out.append("<%s>%s</%s>" % (tag, H.escape(b.get("text") or ""), tag))
            elif tag == "p":
                if b.get("sentences"):
                    out.append("<p>%s</p>" % H.escape(" ".join(norm(s) for s in b["sentences"]), quote=False))
            elif tag == "html":
                out.append(b.get("html") or "")
        if section is not None:
            out.append("</section>")
        out += ["", "</main>", "</body>", "</html>", ""]
        return "\n".join(out)


def from_html(html_text: str) -> Page:
    """A stored (agent-written) page as a page model, for the replay: every <p> of prose becomes a sentence list;
    headings are kept; nothing else matters to a sentence-level comparison."""
    body = ledger.body_only(html_text)
    blocks = []
    for m in re.finditer(r"<(h2|h3|p)\b[^>]*>(.*?)</\1>|<div class=\"src\">(.*?)</div>", body, re.S | re.I):
        if m.group(1) and m.group(1).lower() in ("h2", "h3"):
            blocks.append({"tag": m.group(1).lower(), "section": "body", "text": norm(ledger.plain(m.group(2)))})
        elif m.group(1):
            blocks.append({"tag": "p", "section": "body",
                           "sentences": [norm(s) for s in ledger.sentences(ledger.plain(m.group(2))) if norm(s)]})
        else:
            blocks.append({"tag": "html", "section": "sources", "html": m.group(0)})
    t = re.search(r"<h1[^>]*>(.*?)</h1>", html_text, re.S)
    return Page({"title": norm(ledger.plain(t.group(1))) if t else "", "blocks": blocks})
