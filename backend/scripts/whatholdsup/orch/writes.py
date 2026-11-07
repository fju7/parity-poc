"""What each orchestrator step may write, derived from what its commands and its code write (advisor's ruling after
trial 1's attempt 8). orch/steps.py takes every step's ownership from here; nothing is written by hand there.

Evidence, two kinds:
  - TRACED: the paid attempts' chains (issues/WHU-OT1-02*/orchestrator/chain.jsonl: each step's file hashes before
    and after) and the $0 replay (publish.py check and the carried ruling.py modes wrote nothing outside rulings/*);
  - CODE: each module's own paths, read from the code. MODULE_WRITES and MODULE_READS together classify EVERY case-
    file name a module mentions (tests/test_whu_orchestrator.py fails on an unclassified one), and COMMAND_MODULES
    says which modules a command can run.

Paths are relative to the case folder; "library:*" is the issue's library record; "{slug}" is the issue's slug.
"""
from __future__ import annotations

PAGE = ("draft/{slug}.html", "draft/page.json")

# module -> the case-folder paths it writes (globs)
MODULE_WRITES = {
    "premise": ("premise.json",),
    "acquire_sources": ("sources.json", "library:*"),
    "source_store": ("library:*", "documents-we-do-not-hold.md"),
    "errata": ("errata.json",),
    "sweep_sources": ("sweeps.json", "sources.json"),
    "canary": ("canary.json",),
    "bindings": ("bindings.json",),
    "quotations": ("quotations.json",),
    "ruling": ("rulings/*",),                                 # rulings, attempts, consistency, for_person, re-asks
    "lean_failsafe": ("rulings/lean_removed.jsonl",),
    "lean_editions": ("rulings/lean_editions.jsonl",),
    "omissions": ("omissions.json", "rulings/omissions.jsonl"),
    "coverage_check": ("coverage.json",),
    "judgements": ("judgements.json",),
    "applied_check": ("rulings/applied_check.jsonl",),
    "factcheck_draft": ("draft/{slug}.html.gate.json*",),
    "source_advocate": ("advocate/*",),                       # runs, briefs, adjudication (also written for omissions)
    "findings": ("gate-findings.json",),
    "conclusion_judge": ("conclusion-review.json",),
    "audit_stage": ("audit/*",),
    "consistency": ("rulings/consistency.jsonl", "audit/*"),
    "changecheck": ("change-reviews.json",),
    "changecheck_coverage": ("orchestrator/changecheck_coverage.json",),
    "publish": (),                                            # `check` writes nothing (traced in the $0 replay)
}

# module -> the case-file names it mentions but only reads (each one checked in its code)
MODULE_READS = {
    "bindings": ("figure-exclusions.json",),                  # a person's declarations: read, never written
    "premise": ("issue.json", "sources.json"),
    "acquire_sources": ("access-routes.json",),
    "source_store": ("index.json", "sources.json"),
    "sweep_sources": (),
    "ruling": ("-adjudication.md", "-briefs.json", ".gate.json", "rule.md", "rule_cite.md", "rule_group.md",
               "rule_group_cite.md", "rule_omission.md", "rule_relevance.md", "sources.json"),
    "factcheck_draft": (".runs.json", "draft_decisions.json", "factcheck_known_errors.json"),
    "source_advocate": ("-briefs.json", "briefs.jsonl", "inputs.json", "quote_checks.jsonl", "routing.json",
                        "state.json"),
    "findings": ("issue.json", "sources.json"),
    "conclusion_judge": ("published.json",),
    "audit_stage": ("human_reads.jsonl", "manifest.json", "read.md", "rule.md", "sources.json", "summary.md"),
    "consistency": ("rulings.jsonl",),
    "coverage_check": ("sources.json",),
    "quotations": (".gate.json", "inherited.json", "sources.json"),
    "applied_check": ("manifest.json", "omissions.json", "rulings.jsonl"),
    "omissions": (),
    "publish": (".gate.json", ".runs.json", "changelog.md", "changes.json", "corrections.md", "gate-acceptances.json",
                "issue.json", "published.json", "reviews.json", "sweeps.json", "watch.json"),
}

# command key ("script" or "ruling.py <mode>") -> the modules whose writes it can make
_RULING_COMMON = ("ruling", "bindings", "lean_failsafe", "coverage_check", "quotations")
COMMAND_MODULES = {
    "premise.py": ("premise",),
    "acquire_sources.py": ("acquire_sources", "source_store"),
    "source_store.py": ("source_store",),
    "errata.py": ("errata",),
    "sweep_sources.py": ("sweep_sources",),
    "canary.py": ("canary",),
    "bindings.py": ("bindings", "quotations"),
    "factcheck_draft.py": ("factcheck_draft",),
    "source_advocate.py": ("source_advocate",),
    "findings.py": ("findings",),
    "conclusion_judge.py": ("conclusion_judge",),
    "audit_stage.py": ("audit_stage", "bindings"),
    "consistency.py": ("consistency",),
    "changecheck.py": ("changecheck",),
    "changecheck_coverage.py": ("changecheck_coverage",),
    "publish.py": ("publish",),
    "ruling.py judgements": _RULING_COMMON + ("judgements",),
    "ruling.py gate": _RULING_COMMON + ("lean_editions", "findings"),
    "ruling.py advocate": _RULING_COMMON + ("source_advocate",),
    "ruling.py omissions": _RULING_COMMON + ("omissions", "source_advocate"),   # attempt 8: the re-asks' adjudication
    "ruling.py conclusions": _RULING_COMMON + ("conclusion_judge",),
    "ruling.py changecheck": _RULING_COMMON + ("changecheck",),
    "ruling.py dangling": _RULING_COMMON,
}

# what each step's own code writes (orchestrator.STEP_CODE), read from the code
_APPLY = PAGE + ("bindings.json",) + MODULE_WRITES["applied_check"] + MODULE_WRITES["lean_failsafe"]
CODE_WRITES = {
    "provenance": (),
    "premise": ("premise.json",),
    "discover": ("sources.json",),
    "acquire": ("sources.json", "corrections/*"),
    "draft": PAGE,
    "bind": PAGE + ("bindings.json",),
    "coverage": PAGE + ("coverage.json", "bindings.json", "rulings/coverage_in_scope.jsonl"),
    "judgements": PAGE + ("bindings.json",),
    "commit": (),
    "apply": _APPLY,
    "audit": _APPLY,
    "overstatement": _APPLY + ("rulings/overstatement.jsonl",),
    "corrections": _APPLY + ("bindings.json", "rulings/corrections.jsonl"),
    "preflight": (),
    "archive": ("private_manifest.txt",),
}
# step code that runs code_apply, which may run `ruling.py dangling` once (GAP-016); code_audit also runs
# consistency.py audit
CODE_COMMANDS = {"apply": ("ruling.py dangling",), "audit": ("ruling.py dangling", "consistency.py"),
                 "overstatement": ("ruling.py dangling",), "corrections": ("ruling.py dangling",)}


def command_key(argv) -> str:
    from pathlib import Path
    script = Path(argv[1]).name
    return "%s %s" % (script, argv[2]) if script == "ruling.py" else script


def derive_owns(step) -> tuple:
    """The globs STEP may write: its commands' modules' writes and its code's writes. KeyError on a command or a
    code name this map does not know (a new one must be classified before it can run)."""
    keys = [command_key(a) for a in step.cmds] + list(CODE_COMMANDS.get(step.code, ()))
    out = []
    for k in keys:
        for m in COMMAND_MODULES[k]:
            out += MODULE_WRITES[m]
    if step.code:
        out += CODE_WRITES[step.code]
    return tuple(dict.fromkeys(out))
