"""Apply the stages' own logs to the page, by code, word for word (docs/whu-orchestrator.md §2.2).

What is applied, oldest first by the log's time:
  - rulings with ruling "accept"/"amend" (applied_check.APPLIED) and apply != False:
    the ruled-on sentence becomes the ruling's text ("" removes it);
  - audit cuts (applied_check.load_cuts): the sentence leaves;
  - omission ADDs (omissions.json, outcome ADD): inserted directly after the sentence they name;
  - lean fail-safe removals (rulings/lean_removed.jsonl, outcome OUTCOME): the sentence leaves.
    A fail-safe STOP on a required line removes nothing (the line stays; the page is Not Ready).

Each record is applied once: the applied ones are listed in orchestrator/applied.jsonl by a key of
(log, line), so a re-run of the applier after a later stage applies only what is new.

THE E2 RULE. bind_changed() refuses to (re)bind a sentence unless it is a sentence an applied
record produced. A finding is settled by its ruling, never by binding the sentence it names.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "orch"))
import applied_check as AC  # noqa: E402
import lean_failsafe as FS  # noqa: E402

from orch.page import Page, NotPlaced, norm, fingerprint, split  # noqa: E402

APPLIED_LOG = "orchestrator/applied.jsonl"


class UnruledBinding(RuntimeError):
    """E2: a binding for a sentence no applied ruling produced."""


def _done(case: Path) -> set:
    p = case / APPLIED_LOG
    if not p.exists():
        return set()
    return {json.loads(l)["key"] for l in p.read_text(encoding="utf-8").splitlines() if l.strip()}


def _mark(case: Path, key: str, op: dict) -> None:
    p = case / APPLIED_LOG
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"key": key, **op}, ensure_ascii=False) + "\n")


def pending(case: Path) -> list[tuple[str, str, dict]]:
    """(key, at, operation) for every record not yet applied, oldest first."""
    done = _done(case)
    out = []
    rulings = AC.load_rulings(case)
    for r in rulings:
        if r.get("ruling") not in AC.APPLIED or r.get("apply") is False:
            continue
        old = AC._ruled_on(r)
        if not old:
            continue
        out.append(("ruling:" + r["_log"], str(r.get("at") or ""),
                    {"op": "replace", "old": old, "new": r.get("text") or "", "why": "ruling " + r["_log"]}))
    for c in AC.load_cuts(case):
        out.append(("cut:" + c["_log"], str(c.get("at") or ""),
                    {"op": "delete", "old": c.get("last_text") or "", "why": "audit cut " + c["_log"]}))
    at_of = {r.get("id"): str(r.get("at") or "") for r in rulings if r.get("id")}
    for e in AC.load_inserts(case, rulings):
        if e.get("after") and e.get("text"):
            # An omission's own "at" is its offsets in the source; the ADD's time is its ruling's.
            out.append(("add:%s:%s" % (e.get("key"), e.get("ruling")), at_of.get(e.get("ruling"), ""),
                        {"op": "insert", "anchor": e["after"], "new": e["text"], "why": "omission ADD",
                         "source": e.get("source"), "at": e.get("at")}))
    for row in FS.load(case):
        if row.get("outcome") == FS.OUTCOME and row.get("sentence"):
            out.append(("failsafe:%s:%s:%s" % (row.get("path"), row.get("finding_key"), row.get("fingerprint")),
                        str(row.get("at") or ""),
                        {"op": "delete", "old": row["sentence"], "why": "lean fail-safe (%s)" % row.get("path")}))
    return sorted((x for x in out if x[0] not in done), key=lambda x: x[1])


def apply_all(case: Path, page: Page) -> list[dict]:
    """Apply every pending record to PAGE (not saved here). Returns the operations; raises NotPlaced."""
    made = []
    for key, _at, op in pending(case):
        if op["op"] == "replace":
            page.replace(op["old"], op["new"], op["why"])
        elif op["op"] == "delete":
            page.delete(op["old"], op["why"])
        elif op["op"] == "insert":
            page.insert_after(op["anchor"], op["new"], op["why"])
        _mark(case, key, op)
        made.append(dict(op, key=key))
    return made


def produced(ops: list[dict]) -> set:
    """The sentences the applied operations put on the page."""
    out = set()
    for op in ops:
        if op["op"] in ("replace", "insert"):
            out |= set(split(op["new"]))
    return out


def bind_changed(sentences: list[str], ops: list[dict]) -> list[str]:
    """The sentences that may be (re)bound after a ruling step: each must be one an applied record produced.
    Raises UnruledBinding otherwise (E2)."""
    ok = produced(ops)
    bad = [s for s in sentences if norm(s) not in ok]
    if bad:
        raise UnruledBinding("no applied ruling produced %d sentence(s) to bind, e.g. %r: a finding is settled "
                             "by its ruling, never by binding the sentence it names (E2)" % (len(bad), bad[0][:100]))
    return [norm(s) for s in sentences]
