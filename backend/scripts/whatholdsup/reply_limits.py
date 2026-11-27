"""The one table of output-token limits for every model call site an orchestrated run can make (advisor's
ruling 1 on the design review of 2026-11-26, study/whu-reliability/next_phase/design_review_2026-11.md §1).

Rules, all four enforced:
  * every model call site reads its limit from LIMITS (no limit is written at a call site; the module constants
    audit_stage.READ_MAX_OUT / RULE_MAX_OUT, ruling.MAX_OUT, orch/google.MAX_OUT, orch/steps.REPLY_LIMITS and
    conclusion_judge's limit are taken from here);
  * every call records its call site in the spend ledger (`call_site`, spend_ledger.call_site), so reply lengths
    are measured per call site, never pooled;
  * each limit is at least twice the longest reply measured for that call site in the ledger's orchestrated rows
    (rows carrying `step`), rounded up to 100 (backend/tests/test_whu_reply_limits.py reads the ledger, $0);
  * in an orchestrated run a cut-off reply is re-asked once with the limit doubled (at most PROVIDER_MAX), inside
    the caps; a second cut-off takes the step's existing fail-safe (audit_stage.Caller, factcheck_draft.call,
    orch/google.Gateway.call).

MEASURED and CENSORED record the basis at 14f3b5c (ledger rows with `step`, trial line whu-lean-orch-t1-). Where
older rows pooled two call sites under one (step, role) -- audit_stage.Caller recorded role "audit" for every
call -- a pooled maximum above a call site's own limit cannot be that site's: a longer reply would have been cut
off and stopped the run, and none was. Such a site's measured maximum is therefore censored at its limit at the
time, and its limit here is twice that limit.
"""
from __future__ import annotations

import os
import re

PROVIDER_MAX = 128000        # Claude Opus 5.5 / Sonnet 5.5 / Sonnet 4.6 maximum output (claude-api reference)

LIMITS = {
    # audit_stage.Caller call sites ------------------------------------------------------------------------
    "premise": 4100,              # measured 2,021 (03b, 2026-11-27; was 1,941, 02w)
    "draft": 30000,               # measured 4,389
    "coverage": 2100,             # measured 1,007 (01d, 2026-11-27; was 1800 against 873, P147); 2x = 2,014
    "judgement-sentence": 1600,   # measured 752 (04g, 2026-11-27; P213); 748 (04e, P205); 676 (04d, P201)
    "premise-reading": 3000,      # 1,500 cut off on 02zd, censored at 1,500 (was a hard-coded 1,500)
    "audit-read": 12000,          # pooled audit-step max 5,813 (<= 12,000: the reader's own); 2x = 11,626
    "audit-rule": 3000,           # censored at its old limit 1,500 (pooled with the reader)
    "ruling": 8000,               # ruling.py, every mode: 967 in its own steps; censored at its old 4,000 in the
                                  # audit step (consistency repeats, pooled with the reader's 5,813)
    # factcheck_draft.call call sites (the label before ":" or "/") ---------------------------------------------
    "fc:discover": 4600,          # measured 2,291 (was 4,000: 1.75x)
    "fc:belief-outlet": 4200,     # measured 2,051 (02zd round 2, not cut off; was a hard-coded 1,500)
    "fc:recency": 64000,          # measured 3,434; factcheck_draft.read_budget's 64,000
    "fc:extract": 64000,          # unmeasured in orchestrated rows; read_budget
    "fc:inference": 64000,        # unmeasured; read_budget
    "fc:coverage": 64000,         # unmeasured; read_budget
    "fc:source": 64000,           # unmeasured; read_budget
    "fc:advocate": 64000,         # measured 8,691
    "fc:advocate-questions": 64000,   # unmeasured
    "fc:advocate-requote": 64000,     # measured 596
    "fc:advocate-reask-omission": 64000,   # measured 134
    "fc:changecheck": 64000,      # measured 451
    "fc:counterexample": 64000,   # unmeasured; counterexample.py (not an orchestrated step)
    "fc:evidence": 64000,         # unmeasured; read_budget
    "fc:conclusion_judge": 600,   # unmeasured in orchestrated rows (conclusion_judge.py's own 600)
    # orch/google.Gateway ------------------------------------------------------------------------------------
    "overstatement": 2800,        # measured 63 here; 1,375 in the study ledger (1,286 thinking); thinking counts
    "google-preflight": 64,       # the paid-tier check; its reply is never read, so never re-asked
}

# Call sites whose reply is never parsed: a cut-off is not a failure there, and is not re-asked.
NO_REASK = {"google-preflight"}

# "-requote" (after the fresh Q1-01, 2026-11-26): the audit reader's re-quote of a passage (audit_stage, role +
# "-requote") belongs to its reader's site; "second-read-requote" had mapped to no site in the table.
_SUFFIX = re.compile(r"-(retry|reask|one-sentence|repeat|summary|escalate|second|cutoff-reask|requote)$")


def sha() -> str:
    """A short hash of the table (LIMITS, PROVIDER_MAX, NO_REASK): the configuration a measured cost was spent under
    (stage_cap.current_config; the orchestrator passes it to every step as WHU_ORCH_LIMITS_SHA)."""
    import hashlib
    import json
    return hashlib.sha256(json.dumps({"limits": LIMITS, "max": PROVIDER_MAX, "no_reask": sorted(NO_REASK)},
                                     sort_keys=True).encode()).hexdigest()[:16]


def site_of_role(role: str) -> str:
    """The call site an audit_stage.Caller role belongs to. Roles are the strings the callers pass: model_steps
    ("premise", "coverage", "judgement_sentence", "premise-reading", "draft"), audit_stage ("read", "read-escalate",
    "read-summary", "rule", "rule-reask", "rule-second", ...), ruling.py ("rule-<kind>", "-retry",
    "-one-sentence") and consistency.py ("rule-<kind>-repeat", "rule-repeat")."""
    r = (role or "").strip()
    while True:
        r2 = _SUFFIX.sub("", r)
        if r2 == r:
            break
        r = r2
    r = r.replace("_", "-")
    if r in ("read", "second-read"):
        return "audit-read"
    if r in ("rule",):
        return "audit-rule"
    if r.startswith("rule-"):
        return "ruling"
    return r


def site_of_label(label: str) -> str:
    """The call site of a factcheck_draft.call label ("advocate:S001" -> "fc:advocate",
    "conclusion_judge/claude-sonnet-4-6" -> "fc:conclusion_judge")."""
    base = re.split(r"[:/]", (label or "call"), maxsplit=1)[0].strip()
    return "fc:" + base


def limit(site: str) -> int:
    """The call site's limit. An unknown call site is refused: a call nobody gave a limit is a call nobody
    measured."""
    if site not in LIMITS:
        raise KeyError("no reply limit for call site %r (add it to reply_limits.LIMITS)" % site)
    return LIMITS[site]


def doubled(n: int) -> int:
    return min(2 * int(n), PROVIDER_MAX)


def orchestrated() -> bool:
    """Inside an orchestrated run (paid, trial, rehearsal or replay): the doubled re-ask applies."""
    return bool(os.environ.get("WHU_ORCH_STEP") or os.environ.get("WHU_ORCH_MODE"))


def cutoff_log(site: str, max_tokens: int, event: str, extra: dict | None = None) -> None:
    """Note a cut-off and its re-ask where the orchestrator counts them (WHU_ORCH_CUTOFF_LOG, one JSON line per
    event; the run record's `cutoff_replies`). Never raises."""
    path = os.environ.get("WHU_ORCH_CUTOFF_LOG")
    if not path:
        return
    try:
        import json
        from datetime import datetime, timezone
        row = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "site": site,
               "max_tokens": int(max_tokens), "event": event, "step": os.environ.get("WHU_ORCH_STEP", "")}
        row.update(extra or {})
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except Exception:
        pass
