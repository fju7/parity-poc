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


# ---------------------------------------------------------------------------
# WHICH INTERPRETER IS RUNNING THIS
#
# On 2026-09-10 every command in a working session ran as
#   V=.venv/bin/python3; [ -x "$V" ] || V=python3
# and there is no `.venv` in this repository -- the project venv is
# `backend/venv`. The fallback fired on every invocation and said nothing. It
# never mattered, because these modules are stdlib-only, until a check needed
# `anthropic` and died on ModuleNotFoundError.
#
# The shape is the one already in the catalogue twice: a guard that catches
# nothing, a row that vanishes on error, and now a fallback that substitutes a
# different interpreter. **The working case and the degraded case are
# indistinguishable from outside.**
#
# So: say which interpreter is running, on stderr, when it is not the project's
# own -- and record it in anything that gets stored, so a stored result carries
# the environment that produced it.
# ---------------------------------------------------------------------------

def project_python() -> Path:
    return Path(__file__).resolve().parents[2] / "venv" / "bin" / "python3"


def interpreter() -> str:
    """The interpreter actually running, for storage beside any result."""
    import sys
    return sys.executable


def announce_interpreter(stream=None) -> bool:
    """Print to stderr when this is not the project venv. Returns True if it was.

    Not an error: running on the system interpreter is fine for stdlib-only
    work. What is not fine is doing it silently, because then a result and a
    result-from-somewhere-else look the same.
    """
    import sys
    # sys.prefix, NOT the executable path. A venv's bin/python3 is a symlink to
    # the base interpreter, so resolving both makes them equal and the check
    # returns "fine" for every interpreter on the machine -- which is what the
    # first version of this function did, an hour after it was written to catch
    # exactly that class of thing. sys.prefix is what actually differs between
    # environments.
    want = project_python().parent.parent          # backend/venv
    if want.exists() and Path(sys.prefix).resolve() == want.resolve():
        return True
    out = stream or sys.stderr
    print("  [interpreter] running %s (prefix %s)"
          % (sys.executable, sys.prefix), file=out)
    if want.exists():
        print("  [interpreter] NOT the project venv at %s -- results stored from "
              "this run carry the interpreter that produced them" % want, file=out)
    else:
        print("  [interpreter] no project venv at %s" % want, file=out)
    return False
