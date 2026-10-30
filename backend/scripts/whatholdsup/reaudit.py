#!/usr/bin/env python3
"""Incremental re-audit (lean WHU item 2), used by audit_stage.run only when
lean.enabled().

After an issue's first full audit, a re-audit reads only:
  * the sentences that changed (a fingerprint the prior run did not read);
  * their immediate neighbours (the sentence before and after, in the same part);
  * every sentence bound to the same passages as a changed sentence (a bound
    span on the same source covering an overlapping passage, passage_index);
  * every sentence resting on a held text whose sha256 changed since the run;
  * every sentence the prior run did not settle (must leave the page, cut, a
    person's read still owed, a failed read).
Every other sentence carries its verdict forward by fingerprint, recorded as
carried with the run it came from (audit_stage logs a "carried" verdict).

A FULL AUDIT INSTEAD, with the reason on the manifest, when: there is no prior
complete run; the prior run was a dry run; the reading, ruling or summary
prompt, or the model, changed; or more than MAX_CHANGED of the sentences
changed.
"""
from __future__ import annotations

import json
from pathlib import Path

import passage_index as P

MAX_CHANGED = 0.25
CARRY_OK = ("holds", "not_a_correction", "updated_by_source", "holds_by_ruling", "holds_by_human_read")
SAME = ("read_prompt_sha256", "rule_prompt_sha256", "summary_prompt_sha256", "model")


def _A():
    import audit_stage as A
    return A


def prior_run(slug: str) -> Path | None:
    """The latest complete, full, not-withdrawn audit run (audit_stage.latest_run's order)."""
    A = _A()
    root = A.audit_root(slug)
    if not root.exists():
        return None
    for p in sorted((p for p in root.iterdir() if (p / "manifest.json").exists()), reverse=True):
        if A.is_withdrawn(p):
            continue
        m = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
        if m.get("status") == "complete" and not m.get("limit"):
            return p
    return None


def prior_units(run_dir: Path) -> list[dict]:
    """[{id, part, sha}] of the units RUN_DIR read, in order: from its
    manifest's unit_list (lean runs) or its verdicts.jsonl (round 0 and 1)."""
    m = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    if m.get("unit_list"):
        return [{"id": i, "part": p, "sha": s} for i, p, s in m["unit_list"]]
    seen, out = set(), []
    vp = run_dir / "verdicts.jsonl"
    for line in (vp.read_text(encoding="utf-8").splitlines() if vp.exists() else []):
        r = json.loads(line) if line.strip() else {}
        if r.get("round") in (0, 1) and r.get("unit") not in seen:
            seen.add(r["unit"])
            out.append({"id": r["unit"], "part": r.get("part"), "sha": r.get("sha")})
    out.sort(key=lambda u: int(str(u["id"]).lstrip("u") or 0))
    return out


def prior_state(run_dir: Path) -> dict[str, str]:
    """The run's final state by fingerprint, with a person's recorded reads applied
    (as audit_stage.preflight_rows applies them)."""
    A = _A()
    m = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    state = dict(m.get("state") or {})
    hr = run_dir / "human_reads.jsonl"
    if hr.exists():
        for line in hr.read_text(encoding="utf-8").splitlines():
            r = json.loads(line) if line.strip() else {}
            if state.get(r.get("sha")) == A.HUMAN_READ_REQUIRED and r.get("verdict") == "holds" \
                    and r.get("by") and r.get("at"):
                state[r["sha"]] = "holds_by_human_read"
    return state


def _passages(u: dict, held: dict, slug: str) -> set[tuple[str, int]]:
    """(source, passage index) of every bound span of U's row."""
    A = _A()
    out = set()
    row = u.get("row") or {}
    for x in [row] + (row.get("also_rests_on") or []) + (row.get("premises") or []):
        sid, span = x.get("source_id"), x.get("span")
        text = held.get("%s:%s" % (slug, sid)) or held.get(sid) if sid else None
        if not (text and span):
            continue
        at = P.find_span(text, span)
        if at:
            out |= {(sid, i) for i in P.index_of(text).covering(*at)}
    return out


def plan(slug: str, us: list[dict], held: dict, manifest: dict, run_dir: Path | None) -> dict:
    """{"mode": "incremental"|"full", "why", "from": run name, "read": [ids],
    "carry": {id: status}, "changed": [ids], "neighbours": [ids],
    "same_passage": [ids], "source_changed": [ids], "unsettled": [ids]}."""
    A = _A()
    full = {"mode": "full", "read": [u["id"] for u in us], "carry": {}}
    if run_dir is None:
        return dict(full, why="no prior complete audit run")
    pm = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    changed_cfg = [k for k in SAME if pm.get(k) != manifest.get(k)]
    if changed_cfg:
        return dict(full, why="%s changed since %s" % (", ".join(changed_cfg), run_dir.name), **{"from": run_dir.name})
    pu = {u["sha"] for u in prior_units(run_dir)}
    st = prior_state(run_dir)
    changed = [u["id"] for u in us if u["sha"] not in pu]
    if us and len(changed) / len(us) > MAX_CHANGED:
        return dict(full, why="%d of %d sentences changed (more than %d%%)" % (
            len(changed), len(us), round(MAX_CHANGED * 100)), **{"from": run_dir.name, "changed": changed})
    ids = [u["id"] for u in us]
    by_id = {u["id"]: u for u in us}
    ch = set(changed)
    neighbours = set()
    for i, u in enumerate(us):
        if u["id"] not in ch:
            continue
        for j in (i - 1, i + 1):
            if 0 <= j < len(us) and us[j]["part"] == u["part"] and us[j]["id"] not in ch:
                neighbours.add(us[j]["id"])
    want = set()
    for i in ch:
        want |= _passages(by_id[i], held, slug)
    same = {u["id"] for u in us if u["id"] not in ch and want and _passages(u, held, slug) & want}
    old_held = (pm.get("inputs") or {}).get("held_texts") or {}
    new_held = (manifest.get("inputs") or {}).get("held_texts") or {}
    moved = {k.split(":")[-1] for k in set(old_held) | set(new_held) if old_held.get(k) != new_held.get(k)}
    src = {u["id"] for u in us if set(A.sources_of(u.get("row"))) & moved}
    unsettled = {u["id"] for u in us if u["id"] not in ch and st.get(u["sha"]) not in CARRY_OK}
    read = ch | neighbours | same | src | unsettled
    return {"mode": "incremental", "from": run_dir.name,
            "why": "%d changed, %d neighbours, %d on the same passages, %d on a changed source, "
                   "%d unsettled; %d carried" % (len(ch), len(neighbours - ch), len(same - ch - neighbours),
                                                 len(src - ch - neighbours - same),
                                                 len(unsettled - ch - neighbours - same - src),
                                                 len(ids) - len(read)),
            "read": [i for i in ids if i in read],
            "carry": {u["id"]: st[u["sha"]] for u in us if u["id"] not in read},
            "changed": changed, "neighbours": sorted(neighbours, key=ids.index),
            "same_passage": sorted(same, key=ids.index), "source_changed": sorted(src, key=ids.index),
            "unsettled": sorted(unsettled, key=ids.index)}
