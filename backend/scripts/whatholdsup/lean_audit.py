#!/usr/bin/env python3
"""Lean WHU's audit inputs (lean.py items 1, 5 and 6), used by audit_stage.run
only when lean.enabled().

WHAT THE READER IS SENT. For each document a batch rests on: the passages its
sentences are bound to (each span widened to the passages that cover it,
passage_index.retrieve) plus, for each sentence, the top-k passages BM25
finds for it -- never the whole source. A sentence whose retrieval finds
nothing above the threshold gets its bound passages alone, and the run's
manifest logs it (`retrieval`, `below_threshold`). The delivery check
(audit_stage.check_delivery) runs on what is sent, as before: every bound span
must be in it.

STABLE GROUP DOCUMENTS (for the cache). audit_stage.batches groups sentences
by the source they rest on first. When a group runs to two or more batches,
each of its batches is sent the same text for that primary source -- the union
of the passages its whole group needs -- placed first among the documents, so
the prompt prefix up to the end of that document is byte for byte the same in
every batch of the group and is read from the cache after the first. If the
union would exceed audit_stage.MAX_DOC_CHARS, batches get their own passages
and nothing is cached.

ESCALATION (model tiering). The first read is the smaller model's
(lean.model_for("audit_first")). A sentence it FLAGS (a finding) or is UNSURE
about is read again by the current model (lean.model_for("audit_escalate")),
whose verdict decides. Unsure, since the frozen reading prompt has no
"unsure" verdict: a quotation still not verbatim after its re-read
(FAILED_READ); "updated_by_source"; or "not_a_correction" on a sentence whose
binding rests on a source (a bound sentence makes a claim about a source, so
calling it apparatus is a doubt, not a verdict). Only "holds" with verbatim
evidence, and "not_a_correction" on an unbound sentence, stand on the smaller
model's read.
"""
from __future__ import annotations

import passage_index as P

ESCALATE_VERDICTS = ("finding", "updated_by_source")


def _A():
    import audit_stage as A
    return A


def spans_on(row: dict | None, sid: str) -> list[str]:
    row = row or {}
    return [x.get("span") for x in [row] + (row.get("also_rests_on") or []) + (row.get("premises") or [])
            if x.get("source_id") == sid and x.get("span")]


def ranges_for(text: str, units: list[dict], sid: str, log: list | None = None) -> list[tuple[int, int]]:
    """The passages UNITS need from one held text: bound plus retrieved."""
    out: list[tuple[int, int]] = []
    for u in units:
        r = P.retrieve(text, u["sentence"], spans_on(u.get("row"), sid))
        out += r["bound"] + [(a, b) for a, b, _s in r["retrieved"]]
        if log is not None:
            log.append({"unit": u["id"], "source": sid, "bound": [list(x) for x in r["bound"]],
                        "retrieved": [list(x) for x in r["retrieved"]],
                        "below_threshold": r["below_threshold"],
                        **({"fallback": "bound passages alone" if r["bound"] else
                            "no bound passage and nothing above threshold: nothing sent from this source"}
                           if r["below_threshold"] else {}),
                        **({"unlocated_spans": len(r["unlocated"])} if r["unlocated"] else {})})
    return P.merge(out)


def batch_docs(slug: str, batch: list[dict], held: dict, licensed: frozenset = frozenset(),
               group_docs: dict | None = None, log: list | None = None) -> dict[str, str]:
    """{source id: passages} for one batch, the primary source first. A source
    in GROUP_DOCS is sent that stable text instead of the batch's own passages."""
    A = _A()
    docs: dict[str, str] = {}
    for sid, (text, _must) in A.doc_passages(slug, batch, held, licensed).items():
        if group_docs and sid in group_docs:
            docs[sid] = group_docs[sid]
            continue
        mine = [u for u in batch if sid in A.sources_of(u.get("row"))]
        rs = ranges_for(text, mine, sid, log)
        if rs:
            docs[sid] = P.deliver(text, rs)
        elif any(spans_on(u.get("row"), sid) for u in mine):
            # Bound spans none of which is in the held text: sent empty, so the
            # delivery check stops the batch (fail closed), as it does today.
            docs[sid] = ""
    if group_docs:
        first = [s for s in group_docs if s in docs]
        docs = {**{s: docs[s] for s in first}, **{s: v for s, v in docs.items() if s not in first}}
    return docs


def batch_inputs(slug: str, batch: list[dict], held: dict, licensed: frozenset = frozenset(),
                 group_docs: dict | None = None, log: list | None = None):
    """audit_stage.batch_inputs, with lean documents: (docs, records)."""
    A = _A()
    _docs, records = A.batch_inputs(slug, [dict(u, row={k: v for k, v in (u.get("row") or {}).items()
                                                       if k == "rests_on_record"}) for u in batch],
                                    held, licensed)
    return batch_docs(slug, batch, held, licensed, group_docs, log), records


def primary(batch: list[dict]) -> str | None:
    A = _A()
    u = batch[0]
    return (A.sources_of(u.get("row")) or [None])[0] if u["part"] not in A.SUMMARY_PARTS else None


def group_documents(slug: str, bs: list[list[dict]], held: dict, licensed: frozenset = frozenset(),
                    log: list | None = None) -> dict[int, dict[str, str]]:
    """{batch index: {primary source: stable text}} for every batch whose
    primary-source group runs to two or more batches and whose union fits."""
    A = _A()
    groups: dict[str, list[int]] = {}
    for i, b in enumerate(bs):
        sid = primary(b)
        if sid and sid not in licensed:
            groups.setdefault(sid, []).append(i)
    out: dict[int, dict[str, str]] = {}
    for sid, idx in groups.items():
        text = held.get("%s:%s" % (slug, sid)) or held.get(sid)
        if len(idx) < 2 or text is None:
            continue
        units = [u for i in idx for u in bs[i] if sid in A.sources_of(u.get("row"))]
        doc = P.deliver(text, ranges_for(text, units, sid, log))
        if doc and len(doc) <= A.MAX_DOC_CHARS:
            for i in idx:
                out[i] = {sid: doc}
    return out


def cache_prefix(prompt: str, sid: str | None) -> str | None:
    """The prompt up to the end of document SID's block, when it is the first
    document in PROMPT; else None."""
    if not sid:
        return None
    head = "<<<DOCUMENT %s\n" % sid
    tail = "\nDOCUMENT %s>>>" % sid
    i = prompt.find("<<<DOCUMENT ")
    if i < 0 or not prompt.startswith(head, i):
        return None
    j = prompt.find(tail, i)
    return prompt[:j + len(tail)] if j >= 0 else None


def needs_escalation(u: dict, v: dict) -> bool:
    A = _A()
    verdict = v.get("verdict")
    if verdict in ESCALATE_VERDICTS or verdict == A.FAILED_READ:
        return True
    if verdict == "not_a_correction" and A.sources_of(u.get("row")):
        return True
    return False
