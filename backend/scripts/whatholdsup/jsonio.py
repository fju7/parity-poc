#!/usr/bin/env python3
"""Write a JSON record back the way it was written.

WHY THIS EXISTS
---------------
On 2026-09-10 two record files were rewritten with `json.dumps(indent=1)` when
the files used `indent=2`. `changes.json` came back as 5,297 changed lines around
191 real ones, and `sources.json` as 1,368 around 7. Both were caught before
committing and both cost more to recover than the edit was worth.

Twice in one day is a pattern, and the fix is smaller than the recovery. Nobody
should have to remember what indentation a file uses; the file already knows.

A record whose diff is mostly formatting cannot be reviewed, and a record that
cannot be reviewed stops being a record.
"""
from __future__ import annotations

import json
import re
from pathlib import Path


def detect_indent(text: str, default: int = 2) -> int:
    """The file's own indentation, from the first indented line."""
    m = re.search(r"^(?:\{|\[)\s*\n(\s+)\S", text)
    return len(m.group(1)) if m else default


def detect_ascii(text: str) -> bool:
    r"""True when the file escapes non-ASCII as \uXXXX."""
    return "\\u" in text


def write(path: str | Path, obj, *, default_indent: int = 2) -> dict:
    """Serialise `obj` to `path` in the format `path` already uses.

    Returns what was detected, so a caller can say so rather than assume.
    """
    p = Path(path)
    old = p.read_text(encoding="utf-8") if p.exists() else ""
    style = {"indent": detect_indent(old, default_indent) if old else default_indent,
             "ensure_ascii": detect_ascii(old) if old else False,
             "trailing_newline": old.endswith("\n") if old else True}
    body = json.dumps(obj, indent=style["indent"],
                      ensure_ascii=style["ensure_ascii"])
    p.write_text(body + ("\n" if style["trailing_newline"] else ""),
                 encoding="utf-8")
    return style


def edit(path: str | Path, fn) -> dict:
    """Read, apply `fn` to the parsed object, write it back unchanged in form."""
    p = Path(path)
    doc = json.loads(p.read_text(encoding="utf-8"))
    out = fn(doc)
    return write(p, doc if out is None else out)
