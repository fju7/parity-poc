#!/usr/bin/env python3
"""Take the answer out of a study capture file, in the form blind.py reads.

The twelve tool answers (~/Projects/whu-study-private/answers/WHU-S0N/) were
saved as capture files: a header of capture metadata, the answer, then lists
the capturing session appended (cited URLs, citation tables, the tool's final
chat message). blind.py was written for the pilot's exports, which were the
answer alone. This module changes no wording. It does three things, by one rule
for every file of a kind:

  1. THE ANSWER IS THE REPORT SECTION. In a .md capture the answer runs from
     the line after its "## Report ..." or "## Full report ..." heading to the
     next capture boundary: a "---" rule or an appended capture heading
     (CAPTURE_END). Claude's "Final chat message" and ChatGPT's launch-turn
     message are outside it, as are the appended URL lists.

  2. CITATION MARKERS BECOME LINKS blind.py already converts. Each marker is
     replaced by a link whose text is its own URL ("[u](u)"), which
     blind.from_markdown turns into a numbered [n] marker before the sentence's
     closing punctuation, as it does Claude's site-name chips:
       - ChatGPT, WHU-S01 and WHU-S02: markers in the page data's form
         ("【46†L181-L190】"); each is looked up in the capture's own
         "Citations (... marker -> title -> URL)" table. A marker the table
         does not list stops the run.
       - ChatGPT, WHU-S03 and WHU-S04: "[[k]](url)".
       - Gemini, WHU-S03 and WHU-S04, from the HTML export (the recorded
         copy, deviations.md 2026-10-22): the superscript citation numerals
         and Gemini's own "[cite: n]" markers, each looked up in the export's
         own "Works cited" list. Google's redirect
         links are decoded to the address they redirect to.
     Gemini, WHU-S01 and WHU-S02 (Markdown exports, where the superscripts
     arrive as numerals glued to the word) are left to blind.py's own Gemini
     rules; works_cited() gives the list their [n] markers number into.
     Claude, WHU-S05 to WHU-S08 (the report panel's "Download as Markdown",
     not page data): escaped "\\[n\\]" markers and the report's own numbered
     "## Sources" list, entry n being [n], as in Gemini's Works cited.
     claude_sources() gives the body without that list and the list's URLs
     (a "[title](url)", "[title](<url>)" or bare "<url>" entry); blind.py reads
     the escaped markers as [n]. A marker the list does not hold, an entry
     out of order or an entry with no URL stops the run.

  3. THE GEMINI HTML BECOMES THE MARKDOWN blind.py reads: headings, paragraphs,
     list items, table rows, links, and each image as "![][imageN]", which is
     how the Markdown export carries Gemini's formula images and which
     blind.py marks as a value the export lost.

A "#:~:text=" fragment is kept in the link; fragment_free() gives the address
a snapshot fetches. Free: no network, no model.
"""
from __future__ import annotations

import html as H
import re
import urllib.parse
from html.parser import HTMLParser

REPORT_START = re.compile(r"^## (Full report|Report)\b")
CAPTURE_END = re.compile(r"^(---\s*$|## (Cited URLs|Citations|Final chat message|Launch-turn|"
                         r"Assistant launch|Unique|URLs in the final))")
LENTICULAR = re.compile(r"【[^】\n]{1,80}】")
CITATION_ROW = re.compile(r"^\s*\d+\.\s*(【[^】]+】)\s*(?:\[\d+-\d+\])?\s*—.*—\s*(https?://\S+)\s*$")
BRACKETED = re.compile(r"\[\[(\d+)\]\]\((https?://[^)\s]+)\)")


class AdaptError(RuntimeError):
    pass


def fragment_free(url: str) -> str:
    return url.split("#", 1)[0]


def report_section(md: str) -> str:
    lines = md.splitlines()
    start = next((i for i, l in enumerate(lines) if REPORT_START.match(l)), None)
    if start is None:
        raise AdaptError("no '## Report' or '## Full report' heading")
    end = next((j for j in range(start + 1, len(lines)) if CAPTURE_END.match(lines[j])), len(lines))
    return "\n".join(lines[start + 1:end]).strip() + "\n"


def chip(url: str) -> str:
    return "[%s](%s)" % (url, url)


def chatgpt_lenticular(md: str) -> str:
    """The report with each 【…】 marker replaced by a link, from the capture's
    citation table."""
    table = {}
    for line in md.splitlines():
        m = CITATION_ROW.match(line)
        if m:
            table.setdefault(m.group(1), m.group(2))
    body = report_section(md)
    missing = sorted({m for m in LENTICULAR.findall(body) if m not in table})
    if missing:
        raise AdaptError("%d citation marker(s) not in the capture's citation table" % len(missing))
    return LENTICULAR.sub(lambda m: " " + chip(table[m.group(0)]), body)


def chatgpt_bracketed(md: str) -> str:
    return BRACKETED.sub(lambda m: chip(m.group(2)), report_section(md))


def claude_sources(md: str) -> tuple[str, list[str]]:
    """Claude's "Download as Markdown" report: (the report up to its
    "## Sources" heading, the URL of each Sources entry in order; entry n is
    [n])."""
    body = report_section(md)
    parts = re.split(r"(?m)^#{1,6}\s*Sources\s*$", body)
    if len(parts) != 2:
        raise AdaptError("%d Sources headings, not one" % (len(parts) - 1))
    text, out = parts[0].rstrip() + "\n", []
    for line in parts[1].splitlines():
        if not line.strip():
            continue
        e = re.match(r"^\s*(\d+)\.\s+(.*)$", line)
        if not e:
            raise AdaptError("Sources line not an entry: %r" % line[:80])
        if int(e.group(1)) != len(out) + 1:
            raise AdaptError("Sources entry %s out of order" % e.group(1))
        u = (re.findall(r"\]\(<(https?://[^>\s]+)>\)?\s*$", e.group(2))
             or re.findall(r"\]\((https?://[^)\s]+)\)?\s*$", e.group(2))
             or re.findall(r"^<(https?://[^>\s]+)>\s*$", e.group(2)))
        if not u:
            raise AdaptError("Sources entry %s has no URL" % e.group(1))
        out.append(u[0])
    if re.search(r"\]\(https?://|<https?://", text):
        raise AdaptError("a link in the report body as well as the Sources list")
    beyond = sorted({int(n) for n in re.findall(r"\\\[(\d+)\\\]", text) if not 1 <= int(n) <= len(out)})
    if beyond:
        raise AdaptError("marker(s) %s not in the Sources list" % beyond)
    return text, out


PPLX_MARK = re.compile(r"\[\^(\d+)\]")
PPLX_ENTRY = re.compile(r"^(\d+)\.\s+\[")


def _pplx_url(line: str) -> str | None:
    """The URL of a References entry's first line, "n. [title](url) - snippet":
    the link after the title's closing "](", taken up to its balanced ")", so
    an address with parentheses in it (cell.com's "S2949-7906(25)00137-5")
    is kept whole."""
    m = re.search(r"\]\((https?://)", line)
    if not m:
        return None
    i, depth = m.start(1), 0
    for j in range(i, len(line)):
        c = line[j]
        if c == "(":
            depth += 1
        elif c == ")":
            if depth == 0:
                return line[i:j]
            depth -= 1
        elif c.isspace():
            return None
    return None


def perplexity_sources(md: str) -> tuple[str, list[str]]:
    """Perplexity's Deep research "Download as Markdown" report: (the report
    up to its "## References" heading with each [^n] footnote marker written
    as [n], the URL of each References entry in order; entry n is [n]).

    report_section() ends the report at Perplexity's own "---" before the
    References, so the list is read from the capture's Report section to the
    capture's own boundary. An entry starts "n. [" with n the next number;
    any other line (a snippet carried over) belongs to the entry above. A
    marker the list lacks, an entry out of order or an entry with no URL
    stops the run."""
    lines = md.splitlines()
    start = next((i for i, l in enumerate(lines) if REPORT_START.match(l)), None)
    if start is None:
        raise AdaptError("no '## Report' heading")
    heads = [i for i in range(start + 1, len(lines)) if re.match(r"^#{1,6}\s*References\s*$", lines[i])]
    if len(heads) != 1:
        raise AdaptError("%d References headings, not one" % len(heads))
    body = report_section(md)
    if body.strip() != "\n".join(lines[start + 1:heads[0]]).rstrip().rstrip("-").strip():
        raise AdaptError("the report does not end at the rule before References")
    out, numbered = [], []
    for line in lines[heads[0] + 1:]:
        if line.startswith("---") or re.match(r"^## (Cited URLs|Citations)\b", line):
            break                                           # the capture's own boundary
        e = PPLX_ENTRY.match(line)
        if e:
            numbered.append(int(e.group(1)))
        if e and int(e.group(1)) == len(out) + 1:
            u = _pplx_url(line)
            if not u:
                raise AdaptError("References entry %s has no URL" % e.group(1))
            out.append(u)
    skipped = [n for n in numbered if n > len(out)]
    if skipped:
        raise AdaptError("References entry %s out of order" % skipped[0])
    if not out:
        raise AdaptError("no References entries")
    if re.search(r"\]\(https?://|<https?://", body):
        raise AdaptError("a link in the report body as well as the References list")
    beyond = sorted({int(n) for n in PPLX_MARK.findall(body) if not 1 <= int(n) <= len(out)})
    if beyond:
        raise AdaptError("marker(s) %s not in the References list" % beyond)
    return PPLX_MARK.sub(r"[\1]", body), out


def works_cited(md: str) -> list[str]:
    """Gemini's Markdown export: the URL of each "Works cited" entry, in order
    (entry n is [n])."""
    body = report_section(md)
    m = re.search(r"(?m)^#{1,6}\s*\**Works cited\**\s*$", body)
    if not m:
        raise AdaptError("no Works cited heading")
    out = []
    for line in body[m.end():].splitlines():
        e = re.match(r"^\s*(?:>\s*)?(\d+)\\?\.\s+(.*)$", line)
        if not e:
            continue
        if int(e.group(1)) != len(out) + 1:
            raise AdaptError("Works cited entry %s out of order" % e.group(1))
        u = re.findall(r"\]\((https?://[^)\s]+)\)", e.group(2)) or re.findall(r"https?://\S+", e.group(2))
        if not u:
            raise AdaptError("Works cited entry %s has no URL" % e.group(1))
        out.append(u[0])
    return out


def _decode(href: str) -> str:
    href = H.unescape(href)
    u = urllib.parse.urlsplit(href)
    if u.netloc in ("www.google.com", "google.com") and u.path == "/url":
        q = urllib.parse.parse_qs(u.query).get("q")
        if q:
            return q[0]
    return href


class _Docs(HTMLParser):
    """Google Docs HTML to the Markdown blind.py reads."""
    BLOCK = {"p": "", "h1": "# ", "h2": "## ", "h3": "### ", "h4": "#### ", "h5": "##### ", "h6": "###### "}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip, self.lists = [], 0, []
        self.href, self.link_text, self.sup = None, [], None
        self.heading, self.in_cited, self.cited, self.cur_li_urls = None, False, [], None
        self.images = 0
        self.row = None

    def emit(self, s):
        if self.sup is not None:
            self.sup.append(s)
        elif self.href is not None:
            self.link_text.append(s)
        elif self.heading is not None:
            self.heading.append(s)
            self.out.append(s)
        elif self.row is not None and self.cell is not None:
            self.cell.append(s)
        elif not self.in_cited:
            self.out.append(s)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("head", "style", "script", "title"):
            self.skip += 1
            return
        if self.skip:
            return
        if tag in self.BLOCK:
            if tag != "p":
                self.heading, self.heading_at = [], len(self.out)
            self.out.append("\n\n" + self.BLOCK[tag])
        elif tag in ("ol", "ul"):
            self.lists.append(tag)
        elif tag == "li":
            if self.in_cited:
                self.cur_li_urls = []
            else:
                self.out.append("\n" + ("1. " if self.lists and self.lists[-1] == "ol" else "- "))
        elif tag == "tr":
            self.row, self.cell = [], None
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif tag == "br":
            self.emit("\n")
        elif tag == "img":
            self.images += 1
            self.emit("![][image%d]" % self.images)
        elif tag == "a" and a.get("href"):
            url = _decode(a["href"])
            if self.in_cited and self.cur_li_urls is not None:
                self.cur_li_urls.append(url)
            self.href, self.link_text = url, []
        elif tag == "span" and "vertical-align:super" in (a.get("style") or "").replace(" ", ""):
            self.sup = []

    def handle_endtag(self, tag):
        if tag in ("head", "style", "script", "title"):
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in self.BLOCK and tag != "p" and self.heading is not None:
            text = " ".join("".join(self.heading).split()).strip("* ")
            self.heading = None
            if text.lower() == "works cited":
                self.in_cited = True
                del self.out[self.heading_at:]            # the heading itself
        elif tag in ("ol", "ul") and self.lists:
            self.lists.pop()
        elif tag == "li" and self.in_cited and self.cur_li_urls is not None:
            if not self.cur_li_urls:
                raise AdaptError("Works cited entry %d has no link" % (len(self.cited) + 1))
            self.cited.append(self.cur_li_urls[0])
            self.cur_li_urls = None
        elif tag in ("td", "th") and self.row is not None and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            cells, self.row = self.row, None
            if not self.in_cited:
                self.out.append("\n| " + " | ".join(cells) + " |")
        elif tag == "a" and self.href is not None:
            url, text = self.href, "".join(self.link_text)
            self.href = None
            if not self.in_cited:
                self.emit("[%s](%s)" % (text, url) if text.strip() else chip(url))
        elif tag == "span" and self.sup is not None:
            nums, self.sup = "".join(self.sup), None
            self.emit("\u2063SUP:%s\u2063" % nums)

    def handle_data(self, data):
        if not self.skip:
            self.emit(data)


def gemini_html(raw: str) -> str:
    """The Markdown blind.py reads, from Gemini's Google Docs HTML export, with
    each superscript citation replaced by links to its Works cited entries."""
    p = _Docs()
    p.feed(raw)
    p.close()
    if not p.in_cited or not p.cited:
        raise AdaptError("no Works cited list in the HTML export")
    md = "".join(p.out)

    def sup(m):
        refs = []
        for n in re.findall(r"\d+", m.group(1)):
            k = int(n)
            if not 1 <= k <= len(p.cited):
                raise AdaptError("superscript %d outside Works cited (1-%d)" % (k, len(p.cited)))
            refs.append(" " + chip(p.cited[k - 1]))
        return "".join(refs)
    md = re.sub("\u2063SUP:([^\u2063]*)\u2063", sup, md)
    # Gemini's own "[cite: n, m]" markers number into the same Works cited list.
    md = re.sub(r"\[cite:\s*([\d,\s]+)\]", sup, md)
    md = re.sub(r"[ \t]+\n", "\n", md)
    return re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"


def gemini_html_counts(raw: str) -> dict:
    p = _Docs()
    p.feed(raw)
    p.close()
    return {"works_cited": len(p.cited), "images": p.images}
