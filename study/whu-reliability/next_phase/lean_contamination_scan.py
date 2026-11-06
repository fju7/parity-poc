#!/usr/bin/env python3
"""Lean test, contamination check (advisor rulings 1, 2026-11-05, and the
broad-command extension of the same day).

    python3 lean_contamination_scan.py <subagent transcript .jsonl> [<paths.tsv>]

Reads the harness's subagent transcript (every tool call's input and result) and
prints one line per tool call (time, tool, command or path) with its flags:

  NAMED     the command or path names a forbidden location (FORBID). The
            subagent's own private archive folder (OWN) is allowed.
  BROAD     the command's SCOPE takes in a forbidden location although none is
            named: a recursive search or listing (grep -r/-R, rg, find, ls -R,
            du, tree, git grep), a whole-tree git read (git diff/log -p/show
            with no pathspec), a shell glob with ** or a code walk (glob.glob,
            os.walk, rglob, Path.glob, os.listdir), run from a root that
            contains one (BROAD_ROOTS: the repo root, issues/, study/,
            backend/tests, ~, ~/Projects, /Users/fredugast, the scratchpad).
            It counts as contamination unless its scope provably excludes the
            forbidden folders; each is reported with its exact text and judged
            by hand.
  SCRATCH   any read of session LT's former scratchpad files (SCRATCH_LT), or
            any listing or broad command over the scratchpad before CLEANED
            (when LT removed its files from it).
  OUTPUT    a tool result mentions a forbidden location (to see what a command
            reached). A mention inside a file the brief requires (CLAUDE.md,
            the process doc, issue.json) is benign; each is read by hand.

Prints commands and paths only, never tool output text. With a second argument,
writes every path-like token read or listed, deduplicated.
"""
from __future__ import annotations

import json
import re
import shlex
import sys

REPO = "/Users/fredugast/Projects/parity-poc-repo"
HOME = "/Users/fredugast"
SCRATCH = "/private/tmp/claude-501/-Users-fredugast/22297bb4-4ffb-4bf4-8c79-e2088e90a001/scratchpad"
CLEANED = "2026-11-05T02:16:00"       # LT removed leandry/, the prompts and its logs from the scratchpad

FORBID = re.compile(r"WHU-Q1-0|whu-quarterly-r1|study/whu-reliability|whu-study-private|round1|/keys/|/scoring/"
                    r"|answers_manifest|key\.json|fixtures/whu_lean|test_whu_lean_scope_notes")
# Another issue's case folder (the brief forbids it; not in the advisor's invalidation list): reported.
OTHER_ISSUE = re.compile(r"issues/(?!WHU-L1-0(\d)(r?)-whu-lean-q1-0\1\2(?![\w]))(?:WHU-[A-Z0-9][\w*?\[\]-]*|[\w-]*\*)")
OWN = re.compile(r"whu-study-private/WHU-L1-0(\d)(r?)-whu-lean-q1-0\1\2(?![\w])")


def rerun(n: str) -> None:
    """A re-run drafter (`--rerun 02`, advisor ruling 2026-11-05, option 2): the
    earlier attempt's case folder, private archive and library record are
    forbidden (NAMED), and the folder is no longer anyone's own."""
    global FORBID, OTHER_ISSUE, OWN
    old = "WHU-L1-%s-whu-lean-q1-%s(?![\\wr])" % (n, n)
    FORBID = re.compile(FORBID.pattern + "|" + old + "|library/issues/whu-lean-q1-%s\\.json" % n)
    OTHER_ISSUE = re.compile(r"issues/(?!WHU-L1-%sr-whu-lean-q1-%sr(?![\w]))(?:WHU-[A-Z0-9][\w*?\[\]-]*|[\w-]*\*)" % (n, n))
    OWN = re.compile(r"whu-study-private/WHU-L1-%sr-whu-lean-q1-%sr(?![\w])" % (n, n))
def rerun_b(n: str, suffix: str = "b") -> None:
    """A second-freeze re-run drafter (`--rerun-b 02`, advisor's rulings after
    Q1-04, 5): EVERY earlier lean attempt at the question (its case folder,
    private archive and library record) is forbidden (NAMED); its own folder is
    WHU-L1-<n>b-whu-lean-q1-<n>b."""
    global FORBID, OTHER_ISSUE, OWN
    olds = ({"01": ["01", "01b"], "04": ["04", "04b"]} if suffix == "c" else
            {"01": ["01"], "02": ["02", "02r"], "03": ["03"], "04": ["04"]})[n]
    pats = []
    for x in olds:
        pats += ["WHU-L1-%s-whu-lean-q1-%s(?![\\w])" % (x, x), "library/issues/whu-lean-q1-%s\\.json" % x]
    FORBID = re.compile(FORBID.pattern + "|" + "|".join(pats))
    OTHER_ISSUE = re.compile(r"issues/(?!WHU-L1-%s%s-whu-lean-q1-%s%s(?![\w]))(?:WHU-[A-Z0-9][\w*?\[\]-]*|[\w-]*\*)"
                             % (n, suffix, n, suffix))
    OWN = re.compile(r"whu-study-private/WHU-L1-%s%s-whu-lean-q1-%s%s(?![\w])" % (n, suffix, n, suffix))


def set_scratch(path: str, cleaned: str) -> None:
    """This session's scratchpad and when LT emptied it (`--scratch DIR --cleaned TS`)."""
    global SCRATCH, CLEANED, BROAD_ROOTS, FORBIDDEN_DIRS
    BROAD_ROOTS -= {SCRATCH, SCRATCH + "/"}
    FORBIDDEN_DIRS = [d for d in FORBIDDEN_DIRS if d != SCRATCH]
    SCRATCH, CLEANED = path.rstrip("/"), cleaned
    BROAD_ROOTS |= {SCRATCH, SCRATCH + "/"}
    FORBIDDEN_DIRS.append(SCRATCH)


SCRATCH_LT = re.compile(r"leandry|prompt_0[1-4]\.txt|scratchpad/contam|scratchpad/full\.txt|scratchpad/t1\.txt")

# Roots whose subtree holds a forbidden folder (relative to the repo root, or absolute).
BROAD_ROOTS = {".", "./", REPO, REPO + "/", "issues", "issues/", "study", "study/", "backend", "backend/",
               "backend/tests", "backend/tests/", "backend/tests/fixtures", "backend/tests/fixtures/",
               "~", "~/", HOME, HOME + "/", "~/Projects", HOME + "/Projects", "/", "..", SCRATCH, SCRATCH + "/",
               "$HOME", "${HOME}", "*", "**"}

RECURSIVE = re.compile(r"(?:^|[\s;&|(`])(?:grep|egrep|fgrep)\s+(?:-\w*[rR]\w*|--recursive|--dereference-recursive)\b"
                       r"|(?:^|[\s;&|(`])(?:rg|find|du|tree|fd)\b"
                       r"|(?:^|[\s;&|(`])ls\s+(?:-\w*R\w*)"
                       r"|(?:^|[\s;&|(`])git\s+grep\b")
GIT_WHOLE = re.compile(r"(?:^|[\s;&|(`])git\s+(?:diff|show|log\s+[^;&|]*-p|log\s+-p)\b")
CODE_WALK = re.compile(r"glob\.glob\(|os\.walk\(|\.rglob\(|\.glob\(|os\.listdir\(|os\.scandir\(|iterdir\(")
STARSTAR = re.compile(r"\*\*")


def _segments(cmd: str) -> list[str]:
    """Split at &&, ||, ;, | and newlines OUTSIDE quotes (a quoted grep pattern
    'a\\|b' is one argument, found 2026-11-05 on Q1-01's 02:08:43 command)."""
    out, cur, q, i = [], [], None, 0
    while i < len(cmd):
        ch = cmd[i]
        if q:
            cur.append(ch)
            if ch == q:
                q = None
            i += 1
            continue
        if ch in "'\"":
            q = ch
            cur.append(ch)
            i += 1
            continue
        if cmd.startswith(("&&", "||"), i):
            out.append("".join(cur)); cur = []; i += 2
            continue
        if ch in ";|\n":
            out.append("".join(cur)); cur = []; i += 1
            continue
        cur.append(ch)
        i += 1
    out.append("".join(cur))
    return [x.strip() for x in out if x.strip()]


def _cwd_after(seg: str, cwd: str) -> str:
    m = re.match(r"cd\s+(\S+)", seg)
    if not m:
        return cwd
    d = m.group(1).strip("'\"")
    if d.startswith("/"):
        return d.rstrip("/") or "/"
    if d in ("~", "$HOME"):
        return HOME
    return (cwd.rstrip("/") + "/" + d).replace("/./", "/")


def _norm(p: str, cwd: str) -> str:
    p = p.strip("'\"")
    if p.startswith("~"):
        p = HOME + p[1:]
    if not p.startswith("/"):
        p = cwd.rstrip("/") + "/" + p if p not in (".", "./") else cwd
    p = re.sub(r"/\./", "/", p).rstrip("/") or "/"
    return p


FORBIDDEN_DIRS = [REPO + "/issues", REPO + "/study", REPO + "/backend/tests/fixtures", REPO + "/backend/tests",
                  HOME + "/Projects/whu-study-private", SCRATCH]


def _covers(root: str) -> bool:
    """Does ROOT's subtree contain a forbidden folder (or is it inside the scratchpad)?
    A glob pattern's scope is the folder before its first wildcard."""
    if any(ch in root for ch in "*?["):
        root = root[:min(root.index(ch) for ch in "*?[" if ch in root)].rsplit("/", 1)[0]
    r = root.rstrip("/") or "/"
    if r.startswith(SCRATCH):
        return True
    if FORBID.search(r) and not OWN.search(r):
        return True
    return any(f == r or f.startswith(r + "/") for f in FORBIDDEN_DIRS)


def _args(seg: str) -> list[str]:
    try:
        toks = shlex.split(seg, posix=True)
    except ValueError:
        toks = seg.split()
    return [t for t in toks[1:] if not t.startswith("-")]


def broad(cmd: str, cwd: str = REPO) -> list[str]:
    """Reasons COMMAND's scope takes in a forbidden folder without naming it ([] if none).
    CWD is the directory the command starts in (the drafter's commands start in the repo
    or in ~, the harness's reset directory; a `cd` inside the command moves it)."""
    out = []
    for seg in _segments(cmd):
        cwd = _cwd_after(seg, cwd)
        if seg.startswith("cd "):
            continue
        if RECURSIVE.search(" " + seg):
            tool = RECURSIVE.search(" " + seg).group(0).split()[-1] if seg else ""
            paths = [a for a in _args(seg) if "/" in a or a in (".", "~", "*", "**") or a.startswith(("~", "$HOME"))]
            if seg.split()[0] in ("grep", "egrep", "fgrep", "rg", "git") and paths and not ("/" in paths[0] or paths[0] in (".", "~")):
                paths = paths[1:]                        # the first plain argument is the pattern
            roots = [_norm(p, cwd) for p in paths] or [cwd]
            for r in roots:
                if _covers(r):
                    out.append("recursive %s over %s" % (seg.split()[0], r))
        if GIT_WHOLE.search(" " + seg) and " -- " not in seg:
            if _covers(cwd) or cwd == REPO:
                out.append("git %s with no pathspec from %s" % (seg.split()[1] if len(seg.split()) > 1 else "", cwd))
        if STARSTAR.search(seg) and _covers(cwd):
            out.append("** glob from %s" % cwd)
    if CODE_WALK.search(cmd):
        for m in re.finditer(r"(?:glob\.glob|os\.walk|os\.listdir|os\.scandir|Path)\(\s*['\"]([^'\"]*)['\"]", cmd):
            if _covers(_norm(m.group(1) or ".", cwd)):
                out.append("code walk over %s" % _norm(m.group(1) or ".", cwd))
        if re.search(r"(?:glob\.glob|os\.walk|os\.listdir|os\.scandir)\(\s*(?:\)|['\"]\.?['\"])", cmd) and _covers(cwd):
            out.append("code walk over the working directory %s" % cwd)
    return sorted(set(out))


NAMES_ONLY = re.compile(r"^(?:ls\b|git\s+status\b|git\s+diff\b.*--name-(?:only|status)|git\s+ls-files\b"
                        r"|(?:grep|egrep|fgrep|rg)\b.*\s-(?:\w*[lLc]\w*|-files-with(?:out)?-matches|-count)\b"
                        r"|find\b(?!.*-exec)|wc\s+-[lc]\b|du\b|tree\b|stat\b|test\b|\[)")


def other_issue_kind(cmd: str) -> str:
    """"names-only" if every part of CMD that touches another issue's folder prints
    names or counts only (ls, grep -l/-c, find without -exec, git status, ...);
    else "CONTENT" (advisor ruling 2026-11-05: content from another issue's folder
    invalidates the run; names only is a breach, ruled case by case)."""
    kinds = []
    for seg in _segments(cmd):
        if OTHER_ISSUE.search(seg):
            kinds.append("names-only" if NAMES_ONLY.search(re.sub(r"^cd\s+\S+\s*", "", seg)) else "CONTENT")
    return "CONTENT" if "CONTENT" in kinds else ("names-only" if kinds else "")


def scratch(cmd: str, ts: str, cwd: str = REPO) -> list[str]:
    out = []
    if SCRATCH_LT.search(cmd):
        out.append("names a former LT scratchpad file")
    if ts < CLEANED:
        for seg in _segments(cmd):
            cwd = _cwd_after(seg, cwd)
            if re.match(r"(?:ls|find|tree|du)\b", seg) or RECURSIVE.search(" " + seg):
                for a in _args(seg) or [cwd]:
                    if _norm(a, cwd).rstrip("/") == SCRATCH or (_norm(a, cwd) == cwd == SCRATCH):
                        out.append("lists the scratchpad before LT cleaned it")
    return out


def calls(path: str):
    uses, results = {}, {}
    for line in open(path):
        try:
            r = json.loads(line)
        except Exception:
            continue
        m = r.get("message") or {}
        for c in m.get("content") if isinstance(m.get("content"), list) else []:
            if c.get("type") == "tool_use":
                uses[c["id"]] = (r.get("timestamp", "")[:19], c["name"], c.get("input") or {})
            if c.get("type") == "tool_result":
                t = c.get("content")
                results[c["tool_use_id"]] = t if isinstance(t, str) else json.dumps(t)
    for i, (ts, name, inp) in uses.items():
        yield ts, name, inp, results.get(i, "")


def text_of(name: str, inp: dict) -> str:
    if name == "Bash":
        return inp.get("command", "")
    return json.dumps({k: v for k, v in inp.items() if k in ("file_path", "path", "pattern", "glob")})


def scan(path: str) -> list[dict]:
    rows = []
    for ts, name, inp, out in calls(path):
        cmd = text_of(name, inp)
        named = sorted(set(x for x in FORBID.findall(cmd)))
        if named and OWN.search(cmd) and set(named) <= {"whu-study-private"}:
            named = []
        b = broad(cmd) if name == "Bash" else []
        if name in ("Grep", "Glob"):
            root = inp.get("path") or REPO
            if _covers(_norm(root, REPO)):
                b = ["%s over %s" % (name, _norm(root, REPO))]
        if name in ("Read",) and (inp.get("file_path") or "").startswith(SCRATCH) and SCRATCH_LT.search(inp["file_path"]):
            b.append("reads a former LT scratchpad file")
        other = sorted(set(m.group(0) for m in OTHER_ISSUE.finditer(cmd)))
        rows.append({"ts": ts, "tool": name, "text": cmd, "named": named, "broad": b, "scratch": scratch(cmd, ts),
                     "other_issue": other, "other_issue_kind": other_issue_kind(cmd) if other else "",
                     "output": sorted(set(FORBID.findall(out)))})
    return rows


PATH_TOKEN = re.compile(r"(?:~|/Users/fredugast|\.{0,2}/)?(?:[\w.\-~]+/)+[\w.\-*]*"
                        r"|\b[\w\-]+\.(?:md|json|jsonl|py|html|txt|pdf|xml)\b")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--rerun" in argv:
        i = argv.index("--rerun")
        rerun(argv[i + 1])
        del argv[i:i + 2]
    if "--rerun-b" in argv:
        i = argv.index("--rerun-b")
        rerun_b(argv[i + 1])
        del argv[i:i + 2]
    if "--rerun-c" in argv:
        i = argv.index("--rerun-c")
        rerun_b(argv[i + 1], "c")
        del argv[i:i + 2]
    if "--scratch" in argv:
        i = argv.index("--scratch")
        j = argv.index("--cleaned")
        set_scratch(argv[i + 1], argv[j + 1])
        for k in sorted([i, j], reverse=True):
            del argv[k:k + 2]
    if not argv:
        print(__doc__)
        return 2
    rows = scan(argv[0])
    for r in rows:
        flags = "".join([" NAMED%s" % r["named"] if r["named"] else "",
                         " BROAD%s" % r["broad"] if r["broad"] else "",
                         " SCRATCH%s" % r["scratch"] if r["scratch"] else "",
                         " OTHER-ISSUE(%s)%s" % (r["other_issue_kind"], r["other_issue"]) if r["other_issue"] else "",
                         " OUTPUT%s" % r["output"] if r["output"] else ""])
        print("%s %-5s %s%s" % (r["ts"], r["tool"], " ".join(r["text"].split())[:230], flags))
    n = {k: sum(1 for r in rows if r[k]) for k in ("named", "broad", "scratch", "other_issue", "output")}
    print("# %d tool calls; flagged: %s" % (len(rows), ", ".join("%s %d" % kv for kv in n.items())))
    for r in rows:
        if r["broad"]:
            print("# BROAD, exact text (%s):\n%s" % (r["ts"], r["text"]))
    if len(argv) > 1:
        seen = {}
        for r in rows:
            for p in PATH_TOKEN.findall(r["text"]):
                p = p.replace(REPO + "/", "")
                if len(p) > 2 and not p.startswith(("http", "//")):
                    seen.setdefault(p, (r["ts"], r["tool"]))
        with open(argv[1], "w") as fh:
            for p, (ts, tool) in sorted(seen.items()):
                fh.write("%s\t%s\t%s\t%s\n" % (p, tool, ts, "FORBIDDEN" if FORBID.search(p) and not OWN.search(p) else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
