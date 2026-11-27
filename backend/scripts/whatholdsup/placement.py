"""Where an omission ADD goes on the page (advisor's ruling 2 on P169, 2026-11-27). $0: no model, no network.

WHU-OT1-01d stopped at omissions: the ruling model's anchor for S003-16 was the code-written fail-safe sentence
"We could not verify where this belief is published." in the limits block. ruling._placement accepted it, because it
searched every page sentence (bindings.page_sentences reads code-written blocks too), while orch/page.Page.insert_after
places only after a sentence of model-written prose (a "p" block), so the applier raised NotPlaced and the run stopped.

THE RULE. An ADD is placed only after a BODY sentence -- a sentence of the page's model-written prose. When the anchor
the ruling names is a code-written sentence (the limits block, the readers' list, a fail-safe or other generated
line), the ADD goes after the LAST body sentence bound to the same source (an on-page binding that is not a readers'-
list line, unprotected); if there is none, there is no place for it, and under lean the finding becomes code's own
"Not added ... (no place on the page)" line on the readers' list (omissions.NOT_ADDED_NO_PLACE), as every other ADD
with no place already does. A protected anchor walks back only over body sentences.

BODY SENTENCES. An orchestrated page keeps its model-written prose as "p" blocks of draft/page.json (orch/page.py);
those sentences are the body. A page with no page.json (a lean run written before the orchestrator) has its body
found by excluding the sentences code writes (code_written).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PAGE_JSON = "draft/page.json"
CODE_WRITTEN_ANCHOR = "the anchor is a code-written sentence"


def _n(s: str) -> str:
    return " ".join((s or "").split())


def code_written(sentence: str) -> bool:
    """SENTENCE is one code writes: a generated limits sentence (lean_sentences frames, the fail-safe belief line),
    a readers'-list heading or line (coverage_check), or a recency/edition count line."""
    import belief_claims as BC
    import lean_sentences as LS
    s = _n(sentence)
    return bool(s) and (s == _n(BC.UNVERIFIED) or LS.is_framed(s))


def page_json_body(case: Path) -> list[str] | None:
    """The page's model-written prose sentences, in order, from draft/page.json; None when the case has none."""
    p = Path(case) / PAGE_JSON
    if not p.exists():
        return None
    doc = json.loads(p.read_text(encoding="utf-8"))
    return [_n(s) for b in doc.get("blocks") or [] if b.get("tag") == "p" for s in b.get("sentences") or []]


def body_set(case: Path | None, sentences: list[str]) -> set[str]:
    """The body sentences among SENTENCES (whitespace-collapsed)."""
    pj = page_json_body(case) if case is not None else None
    if pj is not None:
        return set(pj)
    return {_n(s) for s in sentences if not code_written(s)}


def place(i: int | None, sents: list[str], rows: dict, body: set[str], source: str | None) -> tuple[str | None, str]:
    """(the body sentence an ADD goes after, how), given I, the index of the ruling's anchor in SENTS (None: not on
    the page). None for the sentence: no place (the reason says why)."""
    import audit_stage as A
    import bindings as B

    def unprotected(s: str) -> bool:
        return B.protected_kind(s, rows.get(B.fingerprint(s))) is None

    if i is None:
        return None, "the anchor is not on the page"
    if _n(sents[i]) in body:
        for j in range(i, -1, -1):
            s = sents[j]
            if _n(s) in body and unprotected(s):
                return s, ("after the anchor" if j == i else
                           "after the nearest unprotected sentence before a protected anchor")
        return None, "no unprotected sentence at or before the anchor"
    # The anchor is code-written: after the last body sentence bound to the same source.
    for s in reversed(sents):
        if _n(s) not in body or not unprotected(s):
            continue
        row = rows.get(B.fingerprint(s)) or {}
        if row.get("on_page") and not B.is_declaration_row(row) and source and source in A.sources_of(row):
            return s, "%s; after the last body sentence bound to %s" % (CODE_WRITTEN_ANCHOR, source)
    return None, "%s and no body sentence is bound to %s" % (CODE_WRITTEN_ANCHOR, source or "its source")


# ---------------------------------------------------------------- the $0 sweep over every recorded case

def _anchor_texts(case: Path) -> dict[str, str]:
    """{fingerprint: sentence} for every sentence this case records: the page now, page.json, bindings rows, and
    the fixed generated sentences."""
    import belief_claims as BC
    import bindings as B
    import source_ledger as L
    out = {}
    try:
        rows = json.loads((case / "bindings.json").read_text(encoding="utf-8")).get("bindings") or {}
    except (OSError, ValueError):
        rows = {}
    for fp, r in rows.items():
        if r.get("sentence"):
            out.setdefault(fp, _n(r["sentence"]))
    for p in sorted((case / "draft").glob("*.html")) if (case / "draft").exists() else []:
        for s in L.sentences(L.plain(p.read_text(encoding="utf-8"))):
            out.setdefault(B.fingerprint(_n(s)), _n(s))
    for s in page_json_body(case) or []:
        out.setdefault(B.fingerprint(s), s)
    out.setdefault(B.fingerprint(BC.UNVERIFIED), BC.UNVERIFIED)
    return out


def sweep(case_list=None) -> dict:
    """Every recorded omission ADD in every case folder: is its anchor a body sentence? Classes: body,
    code_written, unresolved (the anchor's text is in none of the case's records)."""
    import os
    os.environ.setdefault("WHU_LEAN", "1")
    root = HERE.parents[2] / "issues"
    cases = case_list or sorted(p for p in root.iterdir() if (p / "omissions.json").exists())
    n, by, rows_out = 0, {"body": 0, "code_written": 0, "unresolved": 0}, []
    for case in cases:
        try:
            om = json.loads((case / "omissions.json").read_text(encoding="utf-8")).get("omissions") or []
        except (OSError, ValueError):
            continue
        texts = None
        pj = page_json_body(case)
        for e in om:
            if e.get("outcome") != "ADD" or not e.get("after"):
                continue
            texts = texts if texts is not None else _anchor_texts(case)
            n += 1
            s = texts.get(e["after"])
            if s is None:
                cls = "unresolved"
            elif code_written(s) or (pj is not None and s not in set(pj) and s not in _added(case)):
                cls = "code_written"
            else:
                cls = "body"
            by[cls] += 1
            if cls != "body":
                rows_out.append({"case": case.name, "key": e.get("key"), "after": e["after"], "class": cls,
                                 "anchor": (s or "")[:160]})
    return {"checked": n, "by_class": by, "outside_body": rows_out}


def _added(case: Path) -> set[str]:
    """Sentences an ADD put on the page and a later step removed again are still body sentences."""
    out = set()
    p = case / "orchestrator" / "applied.jsonl"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("op") in ("insert", "replace") and r.get("new"):
                    new = r["new"] if isinstance(r["new"], list) else [r["new"]]
                    out |= {_n(x) for x in new}
                if r.get("op") in ("replace", "delete") and r.get("old") and not r.get("cascade_of"):
                    out.add(_n(r["old"]))
    return out


def main(argv=None) -> int:
    got = sweep()
    print(json.dumps(got, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
