#!/usr/bin/env python3
"""How much held source text a case folder's COMMITTED files carry (advisor's ruling 4 on P222; the repo is public).

    orch/run_env.py <slug> -- python orch/source_text_scan.py <slug> [--all]

Reads every committed file under the case's audit/ folder (with --all, every committed file of the case) from git
HEAD, never the working tree. In each JSON string value it finds runs of consecutive words that occur word for word
in a held document of the case (8-word shingles, whitespace and case folded), and, apart, the runs that are NOT
also on the case's own page (draft/<slug>.html at HEAD: the page publishes its quotations) nor in a source's
registry title (sources.json). Prints COUNTS ONLY -- per file the
strings carrying a run, the longest run in words, and the words in runs of 8 or more -- never the text. Read-only.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
ROOT = HERE.parents[2]
N = 8
WORD = re.compile(r"[\w’']+", re.U)


def words(s: str) -> list[str]:
    return [w.lower().replace("’", "'") for w in WORD.findall(s or "")]


def shingles(held: dict[str, str]) -> set[tuple]:
    out = set()
    for t in held.values():
        w = words(t)
        out.update(tuple(w[i:i + N]) for i in range(len(w) - N + 1))
    return out


def runs(s: str, sh: set) -> list[int]:
    """Lengths in words of each maximal run of S found in the held text (runs of N words or more)."""
    w = words(s)
    out, i, cur = [], 0, 0
    for i in range(len(w) - N + 1):
        if tuple(w[i:i + N]) in sh:
            cur = cur + 1 if cur else N
        elif cur:
            out.append(cur)
            cur = 0
    if cur:
        out.append(cur)
    return out


def strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v)


def file_strings(text: str, name: str):
    if name.endswith(".jsonl"):
        for line in text.splitlines():
            try:
                yield from strings(json.loads(line))
            except ValueError:
                yield line
    elif name.endswith(".json"):
        try:
            yield from strings(json.loads(text))
        except ValueError:
            yield text
    else:
        yield text


def scan(slug: str, everything: bool = False) -> dict:
    import ruling as R
    import source_store as store
    case = store.case_dir(slug)
    rel = case.relative_to(ROOT).as_posix()
    held = R.held_texts(slug)
    sh = shingles(held)
    page = subprocess.run(["git", "-C", str(ROOT), "show", "HEAD:%s/draft/%s.html" % (rel, slug)],
                          capture_output=True, text=True).stdout
    try:
        titles = " \n ".join(x.get("title") or "" for x in json.loads((case / "sources.json").read_text(
            encoding="utf-8")).get("sources") or [])
    except (OSError, ValueError):
        titles = ""
    published = shingles({"page": page, "titles": titles})
    beyond = sh - published
    pat = rel + ("/" if everything else "/audit/")
    files = [f for f in subprocess.run(["git", "-C", str(ROOT), "ls-files", "--", rel], capture_output=True,
                                       text=True, check=True).stdout.split() if f.startswith(pat)]
    out = {"slug": slug, "held_documents": len(held), "files": {}}
    for f in files:
        text = subprocess.run(["git", "-C", str(ROOT), "show", "HEAD:" + f], capture_output=True, text=True).stdout
        n, longest, total, nb, lb = 0, 0, 0, 0, 0
        for s in file_strings(text, f):
            r = runs(s, sh)
            if r:
                n += 1
                longest = max(longest, max(r))
                total += sum(r)
            b = runs(s, beyond)
            if b:
                nb += 1
                lb = max(lb, max(b))
        out["files"][f[len(rel) + 1:]] = {"strings_with_source_text": n, "longest_run_words": longest,
                                          "words_in_runs": total, "strings_beyond_page": nb,
                                          "longest_run_beyond_page": lb}
    return out


def main(argv=None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    if not a:
        print(__doc__)
        return 2
    print(json.dumps(scan(a[0], "--all" in a), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
