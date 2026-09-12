#!/usr/bin/env python3
"""Structural validity of the pages we serve — the dimension nothing measured.

WHY THIS EXISTS
---------------
On 2026-09-10 the homepage went out with `<a href="/melanoma#updates">14
corrections</a>` **inside** the card's own `<a>`. Nested anchors are invalid: a
browser closes the outer link at the inner one, so every fact after "14
corrections" fell outside the clickable card. It was served for twenty minutes.

**Every check in this repository passed it, and each was right about the only
thing it could see.** `ledger.plain()` of the broken page is byte-identical to
`ledger.plain()` of the fixed one, and every control from rule 1 to the passage
stage works downstream of that extraction. The page was verified after deploying
by reading its rendered text — the one artefact that survives broken markup
intact.

A REGION AND A DIMENSION ARE DIFFERENT COVERAGE GAPS
-----------------------------------------------------
The change log is a **region** nobody governs: enumerate the parts of a page, ask
which controls reach each, and it shows up. Markup was a **dimension** nobody
measured: every region *is* covered, along the one axis anybody instrumented, so
no inventory finds it. **You cannot enumerate your way to a dimension nobody has
thought of.**

WHAT IT CHECKS, AND WHY ONLY THESE
-----------------------------------
Four rules, each decidable from a tag stack:

    UNCLOSED     an element still open at end of document
    MISMATCH     an end tag that is not the innermost open element
    NESTING      <a> in <a>, <p> in <p>, <form> in <form>
    DUPLICATE ID two elements sharing an id -- which silently breaks every
                 #fragment link, including the #updates anchor the issue cards
                 point at

Not a full HTML5 content model. **A check that needs a spec appendix to explain a
failure gets argued with rather than fixed**, and the four above are unambiguous
from a stack alone.

FALSE POSITIVES ARE THE RISK, so the tolerances are stated
------------------------------------------------------------
Void elements never close. Optional end tags (`<li>`, `<p>`, `<td>` and their
kin) close implicitly and are not reported as mismatches when an ancestor closes
over them. Both are the first thing a naive stack gets wrong, and getting them
wrong would make this file noise.
"""
from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

OK, BAD, WARN = "ok", "BLOCKED", "warn"   # publish.py's vocabulary; " STOP" is the display mark

# A void element never closes. The first run of furniture.py's parser reported
# every <br> as unclosed for this reason; the list is copied from there.
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}

# Elements whose end tag is optional in HTML: an ancestor closing over one of
# these is correct markup, not a mismatch.
OPTIONAL_END = {"li", "p", "dt", "dd", "td", "th", "tr", "thead", "tbody",
                "tfoot", "option", "optgroup", "rt", "rp"}

# An element of this kind may never contain another of the same kind.
NO_SELF_NEST = {"a", "p", "form", "button"}


class _Structure(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, int]] = []          # (tag, line)
        self.problems: list[dict] = []
        self.ids: dict[str, int] = {}

    def _say(self, kind, detail, line=None):
        self.problems.append({"kind": kind, "detail": detail,
                              "line": line or self.getpos()[0]})

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        for k, v in attrs:
            if k.lower() == "id" and v:
                if v in self.ids:
                    self._say("DUPLICATE ID",
                              "id=%r appears at line %d and again here; every "
                              "#%s link resolves to only one of them"
                              % (v, self.ids[v], v))
                else:
                    self.ids[v] = self.getpos()[0]
        if tag in NO_SELF_NEST:
            for open_tag, line in self.stack:
                if open_tag == tag:
                    self._say("NESTING",
                              "<%s> inside a <%s> opened at line %d — invalid, "
                              "and a browser closes the outer one here"
                              % (tag, tag, line))
                    break
        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag.lower() not in VOID and self.stack and self.stack[-1][0] == tag.lower():
            self.stack.pop()

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in VOID:
            return
        if not any(t == tag for t, _ in self.stack):
            self._say("MISMATCH", "</%s> with no matching open tag" % tag)
            return
        # Close implicitly-closable elements sitting above it without complaint.
        while self.stack and self.stack[-1][0] != tag:
            top, line = self.stack.pop()
            if top not in OPTIONAL_END:
                self._say("MISMATCH",
                          "</%s> closes over <%s>, opened at line %d and never "
                          "closed" % (tag, top, line))
        if self.stack:
            self.stack.pop()

    def finish(self):
        for tag, line in self.stack:
            if tag not in OPTIONAL_END:
                self._say("UNCLOSED", "<%s> opened here and never closed" % tag, line)
        return self.problems


def check(html: str) -> list[dict]:
    p = _Structure()
    try:
        p.feed(html)
        p.close()
    except Exception as exc:                              # noqa: BLE001
        return [{"kind": "UNPARSEABLE", "detail": "%s: %s" % (type(exc).__name__, exc),
                 "line": 0}]
    return p.finish()


def check_file(path) -> list[dict]:
    return check(Path(path).read_text(encoding="utf-8", errors="replace"))


def pages():
    root = Path(__file__).resolve().parents[3] / "site" / "whatholdsup"
    return sorted(root.glob("*.html")) + sorted(root.glob("email/*.html"))


def preflight_rows(slug: str | None = None) -> list[tuple[str, str, str]]:
    bad = []
    for p in pages():
        for f in check_file(p):
            bad.append("%s:%d %s — %s" % (p.name, f["line"], f["kind"], f["detail"]))
    return [("the markup we serve", OK if not bad else BAD,
             "%d page(s) structurally valid" % len(pages()) if not bad else
             "%d structural defect(s): %s" % (len(bad), " || ".join(bad[:4])))]


def main() -> int:
    n = 0
    for p in pages():
        found = check_file(p)
        n += len(found)
        print("  %-30s %s" % (p.name, "ok" if not found else "%d problem(s)" % len(found)))
        for f in found:
            print("      line %-5d %-13s %s" % (f["line"], f["kind"], f["detail"]))
    print("\n  %d problem(s) across %d page(s)\n" % (n, len(pages())))
    return 1 if n else 0


if __name__ == "__main__":
    raise SystemExit(main())
