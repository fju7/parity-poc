"""One file to hand an outside reviewer: the prompt, the piece, the appendices.

WHY THIS EXISTS
---------------
Until now a review went out as two things a person had to assemble by hand --
`docs/whatholdsup-outside-review-prompt.md` and a copy of the page -- and the
page copy was worse than it looked. It links `/style.css` by absolute path, so
opened on its own it rendered with no styling at all, while the prompt told the
reviewer to "read it as a reader would". A reader would not have read that.

This builds ONE self-contained HTML file: the reviewer's prompt, the piece with
its stylesheet inlined, and Appendices A to D. Nothing to assemble, nothing
that 404s, and no way for the prompt and the packet to name different things.

The content comes from `review_packet.py`, so the .md packet and this .html
bundle cannot drift. Only the rendering is here.

WHAT IS DELIBERATELY NOT IN IT
------------------------------
Our gate report, our findings and our adjudication record. A reader shown our
findings anchors on them, and independence is the whole asset.

Trust boundary: hand-written prose (the prompt, Appendix C, the intros) is
rendered through Markdown. Everything drawn from the bindings, the source store
or the page -- spans, titles, sentences -- is escaped and placed into HTML
directly, never through Markdown, because a span containing an underscore or an
asterisk would otherwise come out silently altered.
"""
import sys, html, re, datetime
sys.path.insert(0, ".")
import review_packet as RP
import markdown

ROOT = RP.ROOT
CSS = ROOT / "site/whatholdsup/style.css"
PROMPT = ROOT / "docs/whatholdsup-outside-review-prompt.md"
FONTS = ("https://fonts.googleapis.com/css2?family=Bitter:ital,wght@0,400;0,500;"
         "0,600;1,400&family=Karla:ital,wght@0,300;0,400;0,500;0,600;1,400"
         "&family=IBM+Plex+Mono:wght@400;500&display=swap")

MD = ("markdown", ["tables", "fenced_code", "sane_lists"])


def md(text: str) -> str:
    return markdown.markdown(text, extensions=MD[1])


def e(text: str) -> str:
    return html.escape(text or "")


def reviewer_prompt() -> str:
    """Everything from '## The prompt' on. What comes before it is addressed to
    us, not to the reviewer, and shipping it would tell them what we withheld."""
    raw = PROMPT.read_text(encoding="utf-8")
    marker = "\n## The prompt\n"
    i = raw.find(marker)
    if i < 0:
        raise SystemExit("PROMPT FILE HAS NO '## The prompt' HEADING — refusing "
                         "to guess where the reviewer-facing half begins.")
    # drop the heading itself: this bundle supplies its own "1 · The prompt".
    body = raw[i + len(marker):]
    # demote one level: the bundle's own sections are h2.
    return re.sub(r"(?m)^(#{2,5}) ", lambda m: "#" * (len(m.group(1)) + 1) + " ", body)


def piece_body() -> str:
    m = re.search(r"<body[^>]*>(.*)</body>", RP.page_html(), re.S | re.I)
    if not m:
        raise SystemExit("could not find <body> in the page")
    return m.group(1)


def appendix_a_html(rows: list[dict]) -> str:
    out = []
    for r in rows:
        prem = "".join(
            "<li><code>%s</code>%s %s</li>"
            % (e(p["source_id"]),
               "" if p["verified"] else
               ' <b class="rv-bad">(SPAN NOT VERIFIED)</b>',
               e(p["span"]))
            for p in r["premises"]) or "<li><i>(none)</i></li>"
        out.append(
            '<div class="rv-inf" id="J%02d"><h4>J%02d</h4>'
            '<p class="rv-claim">%s</p>'
            '<p class="rv-lbl">Rests on</p><ul class="rv-prem">%s</ul>'
            '<p class="rv-lbl">The step we take</p><p>%s</p></div>'
            % (r["n"], r["n"], e(r["sentence"]), prem, e(r["step"])))
    return "\n".join(out)


def appendix_b_html(rows: list[dict]) -> str:
    body = "".join(
        '<tr class="%s"><td><code>%s</code></td><td>%s</td><td>%s</td><td>%s</td></tr>'
        % ("rv-unread" if r["unread"] else "", e(r["id"]), e(r["state"]),
           e(r["title"]),
           "<b class=\"rv-bad\">could not read in full</b>" if r["unread"] else "")
        for r in rows)
    return ('<div class="tablewrap"><table><thead><tr><th>id</th><th>access</th>'
            '<th>title</th><th></th></tr></thead><tbody>%s</tbody></table></div>'
            % body)


def coverage_html() -> str:
    """Appendix D. The status lines are ours; the sentences come off the page,
    so they are escaped rather than rendered."""
    text = RP.coverage_md()
    bullets, sentences, in_list = [], [], False
    for line in text.splitlines():
        if line.startswith("The sentences no role has read"):
            in_list = True
            continue
        if in_list and line.strip():
            sentences.append(re.sub(r"^\s*\d+\.\s*", "", line))
        elif line.startswith("- "):
            bullets.append(line[2:])
    out = "<ul>%s</ul>" % "".join(
        "<li>%s</li>" % md(b).replace("<p>", "").replace("</p>", "")
        for b in bullets)
    if sentences:
        out += ('<p class="rv-lbl">The sentences no role has read</p>'
                '<ol class="rv-unseen">%s</ol>'
                % "".join("<li>%s</li>" % e(s) for s in sentences))
    return out


CHROME = """
.rv-brief { padding-top: 2.5rem; }
.rv-band { background: var(--accent-bg); border: 1px solid var(--rule);
  border-radius: 6px; padding: 1.4rem 1.5rem .6rem; margin: 0 0 2.5rem; }
.rv-band p, .rv-band li { max-width: none; }
.rv-eyebrow { font-family: "IBM Plex Mono", monospace; font-size: .74rem;
  letter-spacing: .12em; text-transform: uppercase; color: var(--accent);
  margin: 0 0 .5rem; }
.rv-brief h2 { margin-top: 3rem; padding-top: 1.1rem;
  border-top: 2px solid var(--rule); }
.rv-brief h3 { margin-top: 1.9rem; font-size: 1.15rem; }
.rv-brief h4 { font-family: "IBM Plex Mono", monospace; font-size: .82rem;
  letter-spacing: .08em; color: var(--accent); margin: 0 0 .45rem; }
.rv-brief ul, .rv-brief ol { max-width: 40rem; color: var(--ink-2);
  padding-left: 1.3rem; margin: 0 0 1.05rem; }
.rv-brief li { margin-bottom: .45rem; }
.rv-brief blockquote { margin: 1.2rem 0; padding: .1rem 0 .1rem 1.1rem;
  border-left: 3px solid var(--accent); }
.rv-brief blockquote p { color: var(--ink); font-weight: 500; }
.rv-brief pre { background: var(--card-2); border: 1px solid var(--rule-soft);
  border-radius: 5px; padding: .9rem 1rem; overflow-x: auto;
  font-family: "IBM Plex Mono", monospace; font-size: .82rem; line-height: 1.5; }
.rv-brief pre code { background: none; padding: 0; font-size: 1em; }
.rv-toc { list-style: none; padding-left: 0; }
.rv-toc li { margin-bottom: .3rem; }
.rv-inf { border-top: 1px solid var(--rule-soft); padding-top: 1.1rem;
  margin-bottom: 1.9rem; }
.rv-claim { color: var(--ink); font-weight: 500; }
.rv-lbl { font-family: "IBM Plex Mono", monospace; font-size: .72rem;
  letter-spacing: .1em; text-transform: uppercase; color: var(--ink-3);
  margin: 0 0 .35rem; }
.rv-prem li, .rv-unseen li { font-size: .93rem; }
.rv-prem code { margin-right: .3rem; }
.rv-bad { color: var(--nope); }
tr.rv-unread td { background: var(--nope-bg); }
.rv-rule { border: 0; border-top: 2px solid var(--rule); margin: 3.5rem 0 0; }
.rv-piece-head { background: var(--card-2); border-radius: 6px;
  padding: 1.1rem 1.5rem; margin: 2.5rem 0 0; }
.rv-piece-head p { max-width: none; margin-bottom: 0; }
"""

INTRO = """This one file is everything you need. It has three parts, and they are
meant to be taken in this order:

1. **The prompt** — what we are asking you to do, what counts as a finding, and
   how to report one.
2. **The piece** — read it straight through, once, as a reader would, before
   you look at any appendix. The appendices name the sentences we are least
   sure of, and reading them first would tell you where to look.
3. **The appendices** — our reasoning, our evidence base, the claims that
   assert nothing exists, and the places our own checks have not been.

A note on the piece as it appears here: it is the live page with its stylesheet
built in, so it reads as a reader sees it. The site navigation at the top and
any link to another issue will not resolve — nothing else is missing."""


def main() -> int:
    today = datetime.date.today().isoformat()
    inf = RP.inferences()
    lib = RP.library()
    sha = RP.page_sha()

    doc = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Outside review — The Melanoma Result</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="%s">
<style>
%s
</style>
<style>
%s
</style>
</head>
<body>

<div class="wrap rv-brief">

<div class="rv-band">
<p class="rv-eyebrow">Outside review · confidential draft</p>
<h1>The Melanoma Result</h1>
<p>A draft article from <b>What Holds Up</b>, sent for independent review before
publication. Built %s. The page reviewed is <code>site/whatholdsup/melanoma.html</code>,
sha256 <code>%s</code>.</p>
<ul class="rv-toc">
<li><a href="#prompt">1 · The prompt — what we are asking you to do</a></li>
<li><a href="#piece">2 · The piece</a></li>
<li><a href="#appendix-a">3 · Appendix A — every inference and its reasoning (%d)</a></li>
<li><a href="#appendix-b">&nbsp;&nbsp;&nbsp;&nbsp;Appendix B — what we hold, and what we could not read (%d)</a></li>
<li><a href="#appendix-c">&nbsp;&nbsp;&nbsp;&nbsp;Appendix C — the universal negatives</a></li>
<li><a href="#appendix-d">&nbsp;&nbsp;&nbsp;&nbsp;Appendix D — where our own machinery has not looked</a></li>
</ul>
</div>

%s

<h2 id="prompt">1 · The prompt</h2>

%s

<h2 id="changed">What has changed since the last outside review</h2>

%s

</div>

<div class="wrap">
<div class="rv-piece-head">
<p class="rv-eyebrow">2 · The piece</p>
<p>Read it straight through before going on to the appendices.</p>
</div>
</div>

<a id="piece"></a>
%s

<div class="wrap rv-brief">
<hr class="rv-rule">

<h2 id="appendix-a">Appendix A — every inference the piece makes, and its reasoning</h2>

%s

%s

<h2 id="appendix-b">Appendix B — what we hold, and what we could not read</h2>

%s

%s

<h2 id="appendix-c">Appendix C — the universal negatives</h2>

%s

<h2 id="appendix-d">Appendix D — where our own machinery has not looked</h2>

%s

%s

%s

</div>
</body>
</html>
""" % (FONTS, CSS.read_text(encoding="utf-8"), CHROME,
       today, sha[:16], len(inf), len(lib),
       md(INTRO),
       md(reviewer_prompt()),
       md(RP.changed_md()),
       piece_body(),
       md(RP.APPENDIX_A_INTRO % (len(inf), RP.spans_line(inf))),
       appendix_a_html(inf),
       md(RP.APPENDIX_B_INTRO), appendix_b_html(lib),
       md(RP.APPENDIX_C),
       md(RP.APPENDIX_D_INTRO), coverage_html(), md(RP.APPENDIX_D_TAIL))

    dest = RP.CASE / "review" / ("%s-for-reviewer.html" % today)
    dest.write_text(doc, encoding="utf-8")
    print("wrote", dest)
    print("inferences:", len(inf), "| failed spans:", RP.failed_spans(inf),
          "| sources:", len(lib), "| bytes:", len(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
