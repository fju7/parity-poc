"""Resume from a checkpoint (Fred's term A2 after orchestrator trial 1 attempt 23, 2026-11-24).

After every step that completes, the orchestrator saves the case folder and the issue's library record as that
step's CHECKPOINT, in the private study folder (WHU_PRIVATE_ROOT, default ~/Projects/whu-study-private/checkpoints/
<slug>/<seq>-<step>/; never the repository: case records quote sources). A paid attempt that stops can then restart
at the failed step (`orchestrator.py run SLUG --mode paid --resume`):

  1. the previous run record (orchestrator/run_paid.json) names the steps that completed and the one that failed;
  2. the chain (orchestrator/chain.jsonl) holds, for each completed step, the hash of every case file after it --
     the checkpoint of the last completed step is VERIFIED against those hashes file by file (a file missing, extra
     or changed refuses the resume: then the run starts from step 1);
  3. the case folder is RESTORED from that checkpoint (whatever the failed step wrote is removed), and the loop's
     state -- the repeat count, the open "changed in this pass", the commit_3b hash, the frozen fingerprints, the
     earlier steps' log -- is rebuilt from the previous record, exactly as the loop would have had it;
  4. the run resumes at the failed step. Its harness manifest is written afresh at the resume (the one from the
     run's start is kept beside it, so a fix made between the stop and the resume is on record, and the
     preflight compares the code the resumed steps ran with).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path

CHAIN = "orchestrator/chain.jsonl"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def root(slug: str) -> Path:
    base = Path(os.environ.get("WHU_PRIVATE_ROOT") or (Path.home() / "Projects" / "whu-study-private"))
    return base / "checkpoints" / slug


def _library_record(slug: str) -> Path:
    from orch import chain as CH
    return CH.library_issues() / ("%s.json" % slug)


def _own(rel: str) -> bool:
    """A file the orchestrator itself writes around every step (orchestrator/*, study_log.md): it may move between
    the chain row and the checkpoint (the study log is written just after the row)."""
    from orch import chain as CH
    import fnmatch
    return any(fnmatch.fnmatch(rel, pat) for pat in CH.ALWAYS_OWNED)


def agrees(current: dict, chain: dict) -> list[str]:
    """Differences between CURRENT hashes and the CHAIN row's, outside the orchestrator's own files."""
    a = {k: v for k, v in current.items() if not _own(k)}
    b = {k: v for k, v in chain.items() if not _own(k)}
    return (["missing %s" % k for k in sorted(set(b) - set(a))] + ["extra %s" % k for k in sorted(set(a) - set(b))] +
            ["changed %s" % k for k in sorted(set(a) & set(b)) if a[k] != b[k]])


def save(case: Path, slug: str, seq: int, step: str, chain_hashes: dict, repo: Path) -> Path:
    """Copy the case (and the library record) as checkpoint SEQ of STEP. What is copied must agree with the chain
    row CHAIN_HASHES (outside the orchestrator's own files); its own hashes are kept in hashes.json, and every copy
    is re-hashed against them."""
    from orch import chain as CH
    hashes = CH.snapshot(case, slug)
    off = agrees(hashes, chain_hashes)
    if off:
        raise RuntimeError("the case moved after step %s's chain row: %s" % (step, "; ".join(off[:5])))
    d = root(slug) / ("%03d-%s" % (seq, step))
    try:
        d.resolve().relative_to(repo.resolve())
        raise RuntimeError("refusing: a checkpoint inside the repository (%s)" % d)
    except ValueError:
        pass
    if d.exists():
        shutil.rmtree(d)
    (d / "case").mkdir(parents=True)
    for rel, sha in hashes.items():
        if rel.startswith("library:"):
            src, dst = _library_record(slug), d / "library" / rel.split(":", 1)[1]
        else:
            src, dst = case / rel, d / "case" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if _sha(dst) != sha:
            raise RuntimeError("checkpoint copy of %s does not match the chain's hash (changed while saving)" % rel)
    (d / "hashes.json").write_text(json.dumps({"step": step, "seq": seq, "hashes": hashes}, indent=1,
                                              sort_keys=True) + "\n", encoding="utf-8")
    return d


def verify(d: Path, chain_hashes: dict) -> list[str]:
    """Checkpoint D's files are exactly those its hashes.json names, each with its hash, and they agree with the
    chain row CHAIN_HASHES outside the orchestrator's own files."""
    try:
        hashes = json.loads((d / "hashes.json").read_text(encoding="utf-8"))["hashes"]
    except (OSError, ValueError, KeyError):
        return ["no readable hashes.json"]
    bad = ["chain: %s" % x for x in agrees(hashes, chain_hashes)]
    have = {}
    for p in (d / "case").rglob("*"):
        if p.is_file():
            have[p.relative_to(d / "case").as_posix()] = p
    for p in (d / "library").rglob("*") if (d / "library").exists() else []:
        if p.is_file():
            have["library:" + p.name] = p
    for rel, sha in hashes.items():
        if rel not in have:
            bad.append("missing %s" % rel)
        elif _sha(have[rel]) != sha:
            bad.append("changed %s" % rel)
    bad += ["extra %s" % rel for rel in sorted(set(have) - set(hashes))]
    return bad


class ResumeRefused(RuntimeError):
    pass


def plan(case: Path, slug: str, record: dict, names: list[str], repeat_steps: set, max_repeats: int,
         keep: int | None = None) -> dict:
    """What a resume needs, rebuilt from the previous RECORD and the chain; ResumeRefused if it cannot be proved.
    NAMES: the steps in order (orch/steps NAMES); REPEAT_STEPS: the names in the repeat group. KEEP: how many of
    the completed steps to keep (a trial resume after a code change keeps those before the earliest changed step:
    advisor's ruling 3 after the A/B build); None keeps them all."""
    from orch import chain as CH
    steps = record.get("steps") or []
    done, failed = [], None
    for s in steps:
        if s.get("failed"):
            failed = s
            break
        done.append(s)
    if failed is None:
        raise ResumeRefused("the previous run has no failed step to resume at (%r)" % (record.get("result") or "")[:120])
    rows = CH.rows(case)
    if len(rows) == len(done) + 1 and rows[-1]["step"] == failed["step"]:
        rows = rows[:-1]          # an outage stopped a step after its chain row was written: it did not complete
    if [r["step"] for r in rows] != [s["step"] for s in done]:
        raise ResumeRefused("the chain's steps %s are not the record's completed steps %s"
                            % ([r["step"] for r in rows][-4:], [s["step"] for s in done][-4:]))
    resume_at = failed["step"]
    if keep is not None and keep < len(done):
        resume_at = done[keep]["step"]
        done, rows = done[:keep], rows[:keep]
    if not rows:
        raise ResumeRefused("no completed step to resume after")
    seq = len(rows) - 1
    d = root(slug) / ("%03d-%s" % (seq, rows[-1]["step"]))
    if not d.exists():
        raise ResumeRefused("no checkpoint for step %d (%s) at %s" % (seq, rows[-1]["step"], d))
    bad = verify(d, rows[-1]["hashes"])
    if bad:
        raise ResumeRefused("checkpoint %s does not match the chain: %s" % (d.name, "; ".join(bad[:5])))
    # the loop's state, as orchestrator.run had it after the last completed step
    repeats, changed = 0, False
    for k, s in enumerate(done):
        code = s.get("code") if isinstance(s.get("code"), dict) else {}
        if s["step"] in repeat_steps and code.get("changed") and s["step"] != "findings":
            changed = True
        if s["step"] == "changecheck" and changed and repeats < max_repeats:
            repeats += 1
            changed = False
    first = None
    for s in done:
        if s["step"] == "commit_3b":
            code = s.get("code") or {}
            first = code.get("head") or (code.get("outcome") or "").replace("committed ", "").strip() or None
    return {"checkpoint": d, "seq": seq, "resume_at": resume_at, "index": names.index(resume_at),
            "repeats": repeats, "changed_in_group": changed, "first": first, "frozen": rows[-1].get("frozen") or {},
            "log": done, "prior_result": record.get("result"), "hashes": rows[-1]["hashes"], "chain": rows}


def restore(case: Path, slug: str, d: Path, keep: tuple = (CHAIN,), chain: list | None = None) -> None:
    """The case folder as checkpoint D saved it (KEEP: paths left alone, the chain), and the library record. CHAIN:
    the verified rows -- the chain is rewritten to them (a row of a step that did not complete is dropped)."""
    for p in sorted(case.rglob("*"), reverse=True):
        rel = p.relative_to(case).as_posix()
        if rel in keep or any(k.startswith(rel + "/") for k in keep):
            continue
        if p.is_file() or p.is_symlink():
            p.unlink()
        elif p.is_dir() and not any(p.iterdir()):
            p.rmdir()
    for p in (d / "case").rglob("*"):
        if p.is_file():
            dst = case / p.relative_to(d / "case")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
    if chain is not None:
        (case / CHAIN).write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in chain),
                                  encoding="utf-8")
    lib = d / "library" / ("%s.json" % slug)
    if lib.exists():
        dst = _library_record(slug)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(lib, dst)


# ---- a run cap raised after the checkpoint (advisor's ruling 1 on Q1-01, 2026-11-26) ----------------------------
# A resume restores issue.json from the checkpoint, so a run cap raised after the stop used to be put back. Now ONE
# field may be carried over: run_cap_usd, only upward, only within caps.json's per-issue cap for the issue, and only
# with an approval given on the command line (--cap-approval), recorded in the run record as a RELAY (who passed it
# on), never as an attestation by the person who approved it. Every other checkpointed record keeps its tamper check
# (verify() above, unchanged); any other difference in the live issue.json is overwritten by the restore, as before.

CAP_FIELD = "run_cap_usd"


def caps_ceiling(caps: dict, slug: str, issue: dict) -> float | None:
    """caps.json's per-issue cap for SLUG, as spend_ledger.cap_for takes its base (per_issue, else the study cap
    for a study issue, else the default)."""
    per = caps.get("per_issue") or {}
    if slug in per:
        return float(per[slug])
    if issue.get("study") is True and caps.get("study_per_issue"):
        return float(caps["study_per_issue"])
    v = caps.get("default_per_issue")
    return float(v) if v else None


def cap_raise(live: dict | None, saved: dict, ceiling: float | None, approval: str | None, at: str) -> dict | None:
    """The run-cap change a resume may carry (None: nothing to carry). LIVE: issue.json in the case before the
    restore; SAVED: the checkpoint's copy. ResumeRefused for a lowered cap, a raise with no approval, or one past
    caps.json's CEILING -- before anything is restored."""
    old, new = (saved or {}).get(CAP_FIELD), (live or {}).get(CAP_FIELD)
    if live is None or new == old:
        return None
    if not isinstance(new, (int, float)) or not isinstance(old, (int, float)) or isinstance(new, bool):
        raise ResumeRefused("issue.json's %s is %r against the checkpoint's %r: only a number may be carried"
                            % (CAP_FIELD, new, old))
    if new < old:
        raise ResumeRefused("issue.json's %s was lowered after the checkpoint ($%.2f -> $%.2f): a resume carries "
                            "a raise only" % (CAP_FIELD, old, new))
    if not (approval or "").strip():
        raise ResumeRefused("issue.json's %s was raised after the checkpoint ($%.2f -> $%.2f) with no approval "
                            "(--cap-approval)" % (CAP_FIELD, old, new))
    if ceiling is None or new > ceiling:
        raise ResumeRefused("issue.json's %s raised to $%.2f is past caps.json's per-issue cap (%s)"
                            % (CAP_FIELD, new, "none" if ceiling is None else "$%.2f" % ceiling))
    return {"field": CAP_FIELD, "old": float(old), "new": float(new), "at": at, "approval_relayed": approval.strip(),
            "relay": "recorded by the orchestrator as relayed on the command line; not an attestation by the "
                     "approver"}


def apply_cap_raise(case: Path, change: dict) -> None:
    """Write the carried run cap into the restored issue.json (the one field; nothing else in the file moves)."""
    p = case / "issue.json"
    text = p.read_text(encoding="utf-8")
    pat = re.compile(r'("%s"\s*:\s*)(-?[0-9.]+)' % CAP_FIELD)
    if len(pat.findall(text)) != 1:
        raise ResumeRefused("issue.json has not exactly one %s to carry the raise into" % CAP_FIELD)
    out = pat.sub(lambda m: m.group(1) + repr(change["new"]), text)
    before, after = json.loads(text), json.loads(out)
    before.pop(CAP_FIELD), after.pop(CAP_FIELD)
    assert before == after
    p.write_text(out, encoding="utf-8")
