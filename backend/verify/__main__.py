"""python -m verify "<citation or identifier>" [--assert TEXT] [--as TEXT] [--payer commercial] [--state OH]

Resolve, fetch and bind one thing, and print what each gate found. A
person's tool: it prints the registry's heading so the reader compares it
with their own eyes, which is how every entry in the golden sets was made.
"""
from __future__ import annotations

import argparse
import sys

from . import law, literature
from .bind import bind_all
from .types import Context


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", help="a citation string, DOI/PMID/PMCID/NCT, or URL")
    ap.add_argument("--assert", dest="assertion", default="", help="what the surface says about it")
    ap.add_argument("--as", dest="characterisation", default=None, help="how the surface characterises it (default: the assertion)")
    ap.add_argument("--payer", default="commercial")
    ap.add_argument("--state", default=None)
    a = ap.parse_args()

    ident = literature.identify(a.what) or law.identify(a.what)
    if ident is None:
        print("RESOLVE   refused: no resolvable identifier in", repr(a.what)); return 2
    mod = literature if ident.registry == "literature" else law
    res = mod.resolve(ident)
    print(f"IDENTIFY  {ident.system}:{ident.value}   ({ident.registry})")
    print(f"RESOLVE   {res.exists.value}   registry={res.registry}   {res.canonical or ''}")
    print(f"HEADING   {res.heading!r}")
    doc = mod.fetch(res)
    print(f"FETCH     {'nothing' if doc is None else f'{doc.kind} via {doc.route}, {len(doc.text):,} chars, sha256 {doc.sha256[:12]}'}")
    if a.assertion or a.characterisation:
        ok, bs = bind_all(a.assertion or a.characterisation, res, doc, Context(a.payer, a.state),
                          characterisation=a.characterisation)
        for b in bs:
            print(f"BIND      {b.kind.value:14} {'ok  ' if b.ok else 'FAIL'}  {b.evidence or b.reason}")
        print("VERDICT  ", "BOUND" if ok else "REFUSED")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
