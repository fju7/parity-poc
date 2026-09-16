"""Every call site of text.normalise / text.normalise_text in verify/, enumerated
by AST, with a ruling on whether its input can be document-length.

WHY: text.normalise strips <tags>. On document-length text a stray "<"
followed anywhere by a ">" deletes everything between; on 2026-09-15 it
swallowed 62k of a 184k-character ACIP page and "favors rejection", present
in the raw text, read as absent. The operator's enumeration found three
document-length sites where the curator had asserted one. This test holds
the scope: a new call site fails it until someone rules on its input; a
document-length site that uses the tag-stripping function fails it.

Reconciled both ways: the table must name every site the AST finds, and
every site in the table must exist.
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
VERIFY = BACKEND / "verify"

# (file, enclosing function, argument as written) -> can the input be document-length?
SITES = {
    ("bind.py", "bind_span", "document.text"): True,                  # the held text
    ("bind.py", "bind_span", "s"): False,                             # a quotation
    ("bind.py", "bind_applicability", 'resolution.heading or ""'): False,
    ("policy.py", "_bind_named", "held.corpus_text()"): True,          # the assertion policy's held material: prompts, claims, documents
    ("policy.py", "_bind_named", "c.text"): False,                    # a lexicon term
    ("publish.py", "link_role", "claim_text"): False,
    ("publish.py", "link_role", "fa"): False,                         # a surname
    ("publish.py", "subject_context", 'c.get("claim_text") or ""'): False,
    ("publish.py", "subject_context", "t"): False,                    # a capitalised token
    ("publish.py", "subject_context", "topic_title"): False,
    ("publish.py", "_source_words", "str(r[k])"): False,              # author / container
    ("publish.py", "work_key", 'src.get("title") or ""'): False,      # a source title (the work fallback key)
    ("publish.py", "works_index", 's.get("title") or ""'): False,     # a source title
    ("publish.py", "works_index", 'w.get("title") or ""'): False,     # a source title
    ("publish.py", "works_index", '(s.get("resolution") or {}).get("heading") or ""'): False,   # a registry / page heading
    ("subject.py", "_present", "term"): False,
    ("subject.py", "extract_terms", "w"): False,
    ("subject.py", "extract_terms", "n"): False,
    ("subject.py", "extract_terms", "assertion"): False,              # a claim
    ("subject.py", "document_frequency", "t"): True,                  # every held document
    ("subject.py", "bind_subject", "expand_abbreviations(raw)"): True,  # the held text + registry text
    ("subject.py", "bind_subject", "assertion"): False,
    ("subject.py", "bind_subject", "w"): False,
    ("text.py", "content_tokens", "s"): False,   # headings, claims; and in supplied.py a BOUNDED 400-char head of a document (a "<" there refuses a title, never admits one)
    ("text.py", "agreement", "ours"): False,     # headings; supplied.py's 400-char head is the bounded exception, conservative
    ("text.py", "agreement", "cand"): False,
}


def _sites():
    found = {}
    for f in sorted(VERIFY.glob("*.py")):
        src = f.read_text(encoding="utf-8")
        tree = ast.parse(src)
        aliases = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "text":
                for a in node.names:
                    if a.name in ("normalise", "normalise_text"):
                        aliases[a.asname or a.name] = a.name
        if f.name == "text.py":
            aliases = {"normalise": "normalise", "normalise_text": "normalise_text"}

        class V(ast.NodeVisitor):
            def __init__(self): self.stack = []
            def visit_FunctionDef(self, n): self.stack.append(n.name); self.generic_visit(n); self.stack.pop()
            def visit_Call(self, n):
                fn = n.func
                name = fn.id if isinstance(fn, ast.Name) else (fn.attr if isinstance(fn, ast.Attribute) else None)
                if name in aliases:
                    arg = ast.get_source_segment(src, n.args[0]) if n.args else ""
                    found.setdefault((f.name, ".".join(self.stack) or "<module>", arg), set()).add(aliases[name])
                self.generic_visit(n)
        V().visit(tree)
    return found


def test_every_normalise_call_site_is_ruled_on_and_document_length_sites_never_strip_tags():
    found = _sites()
    unruled = set(found) - set(SITES)
    stale = set(SITES) - set(found)
    assert not unruled, f"new normalise call site(s) with no ruling on input length: {sorted(unruled)}"
    assert not stale, f"table names call site(s) that no longer exist: {sorted(stale)}"
    for site, resolved in found.items():
        if SITES[site]:
            assert resolved == {"normalise_text"}, f"document-length input through the tag-stripping normaliser at {site}: {resolved}"
        else:
            assert resolved <= {"normalise", "normalise_text"}


def test_the_ruled_document_length_sites_are_exactly_three_plus_subject():
    doc_sites = sorted(k for k, v in SITES.items() if v)
    assert [s[:2] for s in doc_sites] == [("bind.py", "bind_span"), ("policy.py", "_bind_named"),
                                            ("subject.py", "bind_subject"), ("subject.py", "document_frequency")]


# ------------------------------------------------------------------ direction
# What the tag strip did at each fixed site, measured -- not predicted.

BAD = "the paper was in fact an elaborate fraud. p<0.05 for the trend; and later >100 children were seen."


def test_span_old_normaliser_failed_conservatively_and_could_also_fail_permissively():
    from verify.text import normalise, normalise_text
    from verify.bind import bind_span
    from verify.types import Document, Identifier
    # conservative: a present quotation read as absent, because "<0.05 ... >" swallowed the text between
    hay_old = normalise("an elaborate fraud. p<0.05 for the trend; and later >100 children")
    assert "for the trend" not in hay_old and "for the trend" in normalise_text("an elaborate fraud. p<0.05 for the trend; and later >100 children")
    # permissive: deleting "<...>" JOINS the fragments around it, minting a phrase the document never contains
    joined = normalise("the paper was in <ref 12> fact an elaborate fraud")   # contains "in fact"? yes, harmless -- now a harmful join:
    minted = normalise("no <x> evidence of fraud")
    assert "no evidence of fraud" in minted                                    # the document said "no <x> evidence" -- the old fold reads "no evidence"
    assert "no evidence of fraud" not in normalise_text("no <x> evidence of fraud")
    # the site as it stands now: a "<" in the document hides nothing and mints nothing
    doc = Document(Identifier("doi", "x"), "", BAD)
    assert bind_span("He called it 'an elaborate fraud' and noted 'for the trend' too.", doc).ok
    assert not bind_span("It said 'fraud p for the trend'.", doc).ok


def test_named_source_old_normaliser_failed_conservatively_and_could_also_fail_permissively():
    from verify.text import normalise, normalise_text
    from verify.policy import Held, _bind_named
    from verify.types import Document, Identifier
    # conservative: "CDC" inside a swallowed span read as not in the material
    held_text = "Background <see the CDC guidance> the rest of the document."
    assert "cdc" not in normalise(held_text) and "cdc" in normalise_text(held_text)
    # permissive: a join can mint an acronym that was never there
    assert "cdc" in normalise("C<b>DC is not a body") and "cdc" not in normalise_text("C<b>DC is not a body")
    # the site as it stands now
    held = Held(documents=[Document(Identifier("url", "h"), "", held_text, kind="record", text_layer="DECLARED_SOUND")])
    out = _bind_named("f", "The CDC guidance says so.", held)
    cdc = [f for f in out if f.kind == "cdc"]
    assert cdc and all(f.ok for f in cdc)
