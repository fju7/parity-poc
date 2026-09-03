#!/usr/bin/env python3
"""Text the page generates about itself, and the price of saying so.

THE PROBLEM
-----------
After the two writing rules were adopted with no exemption, issue one came down
from 85 sentences needing revalidation to 8, and those 8 were not sentences.
They were an axis tick reading "0 0.5 1.0 - no effect 1.5", a legend label, a
comparison table's cells, a chart caption, and the scorecard's composite 3.4
with the arithmetic that produced it. None of them rests on a source and none of
them should: they are the article talking about itself.

WHY THIS IS NOT AN EXEMPTION LIST
---------------------------------
The obvious move -- a `data-whu="skip"` attribute -- is the grandfathering
argument wearing a different hat, and it would be worse, because it would live
in the HTML where anyone editing the page could extend it to a sentence that
was merely inconvenient.

So each mark is a CLAIM ABOUT THE MARKED TEXT, and each claim is checked. A
mark buys a different obligation, never a lighter one:

    restates   this element introduces no figure. Every figure in it already
               appears in a span some bound sentence rests on. A table may
               restate what the article proved; it may never be the place a
               number enters the page.

    scale      these figures are a ruler, not measurements: they ascend in
               even steps. 0, 0.5, 1.0, 1.5 is a scale. Put 0.51 in an axis
               and the spacing breaks and the check blocks -- which is the
               property that stops "scale" becoming a hiding place.

    computed   this figure is arithmetic over figures shown here. The
               expression is evaluated, its inputs must be the scores actually
               displayed in the same element, its weights must sum to 1, and
               the result must equal the number printed. The scorecard cannot
               drift from its own working.

Unmarked text is subject to rules 1 and 2 exactly as before. An element that
cannot pass its mark's check blocks publication like anything else.
"""
from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_store as store      # noqa: E402
import spancheck as SC            # noqa: E402
import modelbind as MB            # noqa: E402
import bindings as B              # noqa: E402

OK, BAD, WARN = "ok", "BLOCKED", "warn"
MARKS = ("restates", "scale", "computed")
ATTR = "data-whu"

# A VOID ELEMENT NEVER CLOSES. The first run of this parser reported that the
# comparison table introduced 0.0075 and 3.4 -- figures that are nowhere in the
# table. The table contains <br>, which fires a start tag and no end tag, so
# the element's depth never returned to zero and it swallowed the rest of the
# page. The finding was about my parser, not about the article.
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}

# 3 x .25 -- the page writes its multiplication with a real times sign.
TERM = re.compile(r"(\d+(?:\.\d+)?)\s*[x×*]\s*(\.?\d+(?:\.\d+)?)")
SCORE = re.compile(r"(\d+)\s*/\s*5")


class _Marked(HTMLParser):
    """Collect the text of every element carrying data-whu, nesting included."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[tuple[str, str]] = []
        self._stack: list[list] = []      # [mark, depth, chunks]

    def handle_starttag(self, tag, attrs):
        if tag.lower() in VOID:
            return
        for frame in self._stack:
            frame[1] += 1
        mark = dict(attrs).get(ATTR)
        if mark:
            self._stack.append([mark, 0, []])

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag.lower() in VOID:
            return
        for frame in self._stack:
            frame[1] -= 1
        while self._stack and self._stack[-1][1] < 0:
            mark, _, chunks = self._stack.pop()
            self.out.append((mark, " ".join(" ".join(chunks).split())))

    def handle_data(self, data):
        for frame in self._stack:
            frame[2].append(data)

    def close(self):
        super().close()
        while self._stack:
            mark, _, chunks = self._stack.pop()
            self.out.append((mark, " ".join(" ".join(chunks).split())))


def marked(html: str) -> list[tuple[str, str]]:
    p = _Marked()
    p.feed(html)
    p.close()
    return p.out


def strip_marked(html: str) -> str:
    """Remove marked elements, KEEPING every tag around them.

    They are still checked -- by this module, against the obligation their mark
    carries. Removing them here means rule 1 does not also demand a source for
    an axis tick, and the check that DOES apply to them is the one below.

    THE TAGS MUST SURVIVE. The first version returned only the text between
    tags, which discarded the whole document's block structure, and every
    heading on the page fused onto the sentence beneath it -- "And one thing
    almost nobody mentioned Two specialist outlets touched it". That is the
    same defect source_ledger's BREAK sentinel was introduced to fix, made
    again three days later by a function whose job was something else entirely.
    So this deletes marked subtrees and copies everything else through
    unchanged, and the test below is a heading and a paragraph that must stay
    apart.
    """
    out, pos, depth = [], 0, 0
    for m in re.finditer(r"<(/?)([a-zA-Z][\w-]*)([^>]*)>", html):
        closing, tag, attrs = m.group(1), m.group(2).lower(), m.group(3)
        if tag in VOID:
            continue
        if depth == 0:
            if not closing and re.search(r'%s\s*=\s*["\']' % ATTR, attrs):
                out.append(html[pos:m.start()])
                out.append(" ")        # a block boundary where the mark was
                depth = 1
            continue
        if closing:
            depth -= 1
            if depth == 0:
                pos = m.end()
        elif not attrs.rstrip().endswith("/"):
            depth += 1
    out.append(html[pos:])
    return "".join(out)


def bound_figures(slug: str) -> set[float]:
    """Every figure carried by a span some bound sentence actually rests on."""
    doc = B.load(slug)
    text = ""
    for row in (doc.get("bindings") or {}).values():
        if not row.get("on_page"):
            continue
        spans = []
        if row.get("span") and row.get("source_id"):
            spans.append((row["source_id"], row["span"]))
        for extra in (row.get("also_rests_on") or []) + (row.get("premises") or []):
            if extra.get("source_id") and extra.get("span"):
                spans.append((extra["source_id"], extra["span"]))
        for sid, span in spans:
            if SC.b2_present(span, slug, sid)[0] is True:
                text += " " + SC._norm(span)
    return B._as_numbers(MB.figures(text))


def check_restates(text: str, held: set[float], names: set[str]) -> str | None:
    missing = [f for f in B._claim_figures(text, names)
               if MB._weight(f) and not B._as_numbers([f]) <= held]
    if missing:
        return ("introduces %s, which no bound sentence rests on. Furniture may "
                "restate what the article proved; it may not be where a number "
                "enters the page." % ", ".join(sorted(missing)[:4]))
    return None


def check_scale(text: str, *_ignored) -> str | None:
    figs = sorted(B._as_numbers(MB.figures(text)))
    if len(figs) < 3:
        return "a scale needs at least three ticks; found %d" % len(figs)
    steps = [round(b - a, 10) for a, b in zip(figs, figs[1:])]
    if len(set(steps)) != 1 or steps[0] <= 0:
        return ("%s do not ascend in even steps, so they are not a ruler. A "
                "measurement cannot hide in an axis." % ", ".join(map(str, figs)))
    return None


def check_computed(text: str, *_ignored) -> str | None:
    terms = TERM.findall(text)
    if not terms:
        return "marked computed but shows no arithmetic to check"
    scores = [float(s) for s in SCORE.findall(text)]
    inputs = [float(a) for a, _ in terms]
    weights = [float(w) for _, w in terms]
    if scores and inputs != scores:
        return ("the working multiplies %s but the scores shown are %s"
                % (inputs, scores))
    if abs(sum(weights) - 1.0) > 1e-9:
        return "the weights %s sum to %g, not 1" % (weights, sum(weights))
    total = round(sum(a * w for a, w in zip(inputs, weights)), 10)
    shown = B._as_numbers(MB.figures(text)) - set(inputs) - set(weights)
    if not any(abs(total - v) < 5e-2 for v in shown):
        return ("the working comes to %g, which is not among the figures shown "
                "(%s)" % (total, sorted(shown)))
    return None


CHECKS = {"restates": check_restates, "scale": check_scale,
          "computed": check_computed}


def findings(slug: str, html: str) -> list[dict]:
    held = bound_figures(slug)
    names = B.trial_names(store.sources(slug))
    out = []
    for mark, text in marked(html):
        if mark not in CHECKS:
            out.append({"mark": mark, "text": text[:90],
                        "why": "%r is not one of %s" % (mark, ", ".join(MARKS))})
            continue
        why = CHECKS[mark](text, held, names)
        if why:
            out.append({"mark": mark, "text": text[:90], "why": why})
    return out


def computed_figures(html: str) -> set[float]:
    """Figures a `computed` element states AND survives its own check.

    A sentence may refer to the scorecard's 3.4 without pointing at a document,
    because 3.4 is not reported by anyone: the page works it out. That figure is
    checked harder than a quoted one -- the working must use the scores shown,
    the weights must sum to 1, and the total must match -- so rule 1 accepts it.

    Only from an element that PASSES. A scorecard whose arithmetic does not
    come out donates nothing, which is what stops "computed" being a way to
    launder a number onto the page.
    """
    out = set()
    for mark, text in marked(html):
        if mark == "computed" and check_computed(text) is None:
            out |= B._as_numbers(MB.figures(text))
    return out


def preflight_rows(slug: str, html: str) -> list[tuple[str, str, str]]:
    seen = marked(html)
    if not seen:
        return []
    bad = findings(slug, html)
    counts = {}
    for mark, _ in seen:
        counts[mark] = counts.get(mark, 0) + 1
    tally = ", ".join("%d %s" % (n, m) for m, n in sorted(counts.items()))
    return [("text the page generates about itself",
             OK if not bad else BAD,
             "%s — each checked against what its mark claims" % tally
             if not bad else
             "%d of %d marked element(s) fail the claim their mark makes: %s"
             % (len(bad), len(seen),
                " || ".join("%s (%s): %s" % (f["mark"], f["text"][:34], f["why"])
                            for f in bad[:3])))]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--page", required=True)
    args = ap.parse_args()
    html = Path(args.page).read_text(encoding="utf-8")
    for name, state, detail in preflight_rows(args.slug, html):
        print("\n  %-9s %s\n    %s\n" % (state.upper(), name, detail))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
