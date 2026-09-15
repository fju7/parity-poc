"""Static assertions are a first-class enforcement locus.

The broker CAA citation ("29 U.S.C. § 1185i", the provider-directory section
cited as CAA §204) sat in a prompt, in a code-written fallback letter, and in
two frontend pages. Only the first is anywhere a model-output gate could ever
reach. So the per-class extractors run over EVERY string literal in backend/
(by AST: comments are not literals and are not scanned) and over the full text
of every source file under frontend/src (JSX text is not a literal, and it is
exactly what a visitor reads).

Two classes are hard failures: LEGAL_PROVISION and IDENTIFIER. A section
number or a DOI typed into our own code or copy is a TYPED assertion nothing
resolved, and there is no allow-list for static text -- either it is removed,
or it is listed in ALLOW with a reason a reviewer signed (a regex that
DETECTS citations legitimately contains citation shapes; a test fixture of
known-bad provisions is supposed to). NAMED_SOURCE is reported, not failed:
"CMS Medicare benchmark rates" in a product description is true and the class
cannot tell it from a relabelling; the count is printed so a jump is visible.

Usage:  python -m verify.lint_literals            (exit 1 on any unallowed hit)
        python -m verify.lint_literals --json     (machine-readable)
"""
from __future__ import annotations

import ast
import collections
import json
import os
import re
import sys
from dataclasses import dataclass, asdict

from .extract import AssertionClass, extract

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = os.path.abspath(os.path.join(BACKEND, ".."))
FRONTEND_SRC = os.path.join(REPO, "frontend", "src")
ALLOW_PATH = os.path.join(BACKEND, "data", "verify", "lint_allow.json")

BACKEND_SKIP_DIRS = {"venv", "__pycache__", "node_modules", "data", "static", "test_data", "migrations"}
FRONTEND_SKIP_DIRS = {"node_modules", "dist", "__tests__"}
FRONTEND_EXT = (".js", ".jsx", ".ts", ".tsx", ".html", ".md")
HARD = (AssertionClass.LEGAL_PROVISION, AssertionClass.IDENTIFIER)
# identifier sub-kinds that are hard in static text; a bare 7-8 digit number in
# source is far more often a fixture id, a timestamp or a phone number
HARD_IDENTIFIER_KINDS = {"doi", "pmid", "pmcid", "nct", "journal_cite"}


@dataclass
class Hit:
    path: str          # repo-relative
    line: int
    cls: str
    kind: str
    text: str
    allowed_by: str = ""


def _allow() -> list[dict]:
    if not os.path.exists(ALLOW_PATH):
        return []
    return json.load(open(ALLOW_PATH, encoding="utf-8"))["allow"]


def _is_allowed(hit: Hit, allow: list[dict]) -> str:
    """The reason string of the first allow entry that covers the hit, else ''.
    An entry names a path (prefix match) and optionally a text pattern."""
    for a in allow:
        if not hit.path.startswith(a["path"]):
            continue
        if a.get("classes") and hit.cls not in a["classes"]:
            continue
        if a.get("pattern") and not re.search(a["pattern"], hit.text):
            continue
        return a["reason"]
    return ""


def _backend_literals():
    for dp, dns, fns in os.walk(BACKEND):
        dns[:] = [d for d in dns if d not in BACKEND_SKIP_DIRS]
        for f in fns:
            if not f.endswith(".py"):
                continue
            p = os.path.join(dp, f)
            try:
                tree = ast.parse(open(p, encoding="utf-8").read(), p)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) >= 8:
                    yield os.path.relpath(p, REPO), node.lineno, node.value


def _frontend_texts():
    if not os.path.isdir(FRONTEND_SRC):
        return
    for dp, dns, fns in os.walk(FRONTEND_SRC):
        dns[:] = [d for d in dns if d not in FRONTEND_SKIP_DIRS]
        for f in fns:
            if f.endswith(FRONTEND_EXT):
                p = os.path.join(dp, f)
                yield os.path.relpath(p, REPO), 1, open(p, encoding="utf-8", errors="replace").read()


def _scan_text(path: str, base_line: int, text: str, allow: list[dict]) -> list[Hit]:
    hits = []
    for cls in (AssertionClass.LEGAL_PROVISION, AssertionClass.IDENTIFIER, AssertionClass.NAMED_SOURCE):
        for c in extract(cls, text):
            if cls is AssertionClass.IDENTIFIER and c.kind not in HARD_IDENTIFIER_KINDS:
                continue
            line = base_line + text.count("\n", 0, c.start)
            h = Hit(path, line, cls.value, c.kind, c.text)
            h.allowed_by = _is_allowed(h, allow)
            hits.append(h)
    return hits


def run() -> dict:
    allow = _allow()
    hits: list[Hit] = []
    for path, line, text in _backend_literals():
        hits += _scan_text(path, line, text, allow)
    for path, line, text in _frontend_texts():
        hits += _scan_text(path, line, text, allow)
    hard = [h for h in hits if h.cls in {c.value for c in HARD} and not h.allowed_by]
    named = collections.Counter((h.path, h.kind) for h in hits if h.cls == AssertionClass.NAMED_SOURCE.value)
    return {"hard_failures": hard, "allowed": [h for h in hits if h.allowed_by and h.cls in {c.value for c in HARD}],
            "named_source_counts": named, "total_hits": len(hits)}


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    r = run()
    if "--json" in argv:
        print(json.dumps({"hard_failures": [asdict(h) for h in r["hard_failures"]],
                          "allowed": [asdict(h) for h in r["allowed"]],
                          "named_source_counts": {f"{p}::{k}": n for (p, k), n in r["named_source_counts"].items()}}, indent=1))
    else:
        print(f"string-literal lint: {r['total_hits']} hits; {len(r['allowed'])} allowed by reason; "
              f"{len(r['hard_failures'])} HARD failures")
        for h in r["hard_failures"]:
            print(f"  FAIL {h.path}:{h.line}  [{h.cls}/{h.kind}]  {h.text!r}")
        by_kind = collections.Counter()
        for (p, k), n in r["named_source_counts"].items():
            by_kind[k] += n
        print("  named sources (reported, not failed): " + ", ".join(f"{k}={n}" for k, n in by_kind.most_common()))
    return 1 if r["hard_failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
