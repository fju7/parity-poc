"""What the orchestrator's commit step may stage (advisor's ruling 4 on P222; the repo is public).

The commit step staged the whole case folder (`git add -- <case>`). WHU-OT1-04i's commit_8 then committed its
audit/ run folders, and the scan of every committed orchestrated case (orch/source_text_scan.py, 2026-11-28) found
held source text beyond what each page publishes in rulings/rulings.jsonl (runs up to 1,505 words: whole assessment
statements sent to the relevance ruling), bindings.json (up to 833), audit/*/rulings.jsonl (113), the advocate
briefs and adjudications (46), audit/*/verdicts.jsonl (38), rulings/premise_checks.jsonl (36) and the removal logs
(29).

Now the step stages ONLY the paths below that exist, and before committing scans each staged file for held text
not on the page (staged_source_text): a run of more than MAX_WORDS consecutive words of a held document that is
neither on the case's page nor in a source's registry title stops the run, nothing committed. Every other file
stays in the working tree (the run reads it from there) and in the private provenance copy (run_manifest.py).
"""
from __future__ import annotations

from pathlib import Path

# Records that carry decisions by offset and hash, registry metadata, the page, or the run's own account.
ALLOW = ("issue.json", "premise.json", "sources.json", "proposals.json", "errata.json", "judgements.json",
         "coverage.json", "omissions.json", "quotations.json", "canary.json", "conclusion-review.json",
         "change-reviews.json", "gate-findings.json", "sweeps.json", "study_log.md", "draft/page.json",
         "draft/{slug}.html", "draft/{slug}.html.gate.json", "draft/{slug}.html.gate.json.runs.json",
         "orchestrator/chain.jsonl", "orchestrator/manifest.json", "orchestrator/run_paid.json",
         "orchestrator/acquire.json", "orchestrator/changecheck_coverage.json",
         "orchestrator/provenance_manifest.json", "orchestrator/dangling_ruled.jsonl", "orchestrator/runs/*.json",
         "rulings/lean_editions.jsonl", "rulings/advocate_reasks.jsonl", "rulings/consistency.jsonl")
# Never staged: they hold source text, or model inputs and outputs that quote it.
NEVER = ("audit/", "advocate/", "bindings.json", "rulings/rulings.jsonl", "rulings/omissions.jsonl",
         "rulings/overstatement.jsonl", "rulings/premise_checks.jsonl", "rulings/lean_removed.jsonl",
         "orchestrator/applied.jsonl")
MAX_WORDS = 25        # longest run beyond the page measured in an allowed record on 2026-11-28: 23 words


def paths(case: Path, slug: str) -> list[Path]:
    """The allowed files of CASE that exist, in ALLOW's order."""
    out = []
    for pat in ALLOW:
        pat = pat.format(slug=slug)
        out += sorted(case.glob(pat)) if "*" in pat else ([case / pat] if (case / pat).exists() else [])
    return [p for p in out if p.is_file() and not refused(p.relative_to(case).as_posix())]


def refused(rel: str) -> bool:
    return any(rel == n or (n.endswith("/") and rel.startswith(n)) for n in NEVER)


def staged_source_text(slug: str, files: list[tuple[str, str]], case: Path) -> list[tuple[str, int]]:
    """[(path, longest run)] for each (path, text) carrying a run of held text beyond the page longer than
    MAX_WORDS words. The page itself is the reference, so it is never flagged."""
    import json as _json
    import ruling as R
    from orch import source_text_scan as T
    sh = T.shingles(R.held_texts(slug))
    page = (case / "draft" / ("%s.html" % slug))
    try:
        titles = " \n ".join(x.get("title") or "" for x in _json.loads((case / "sources.json").read_text(
            encoding="utf-8")).get("sources") or [])
    except (OSError, ValueError):
        titles = ""
    beyond = sh - T.shingles({"page": page.read_text(encoding="utf-8") if page.exists() else "", "t": titles})
    bad = []
    for name, text in files:
        longest = max((max(r) for r in (T.runs(s, beyond) for s in T.file_strings(text, name)) if r), default=0)
        if longest > MAX_WORDS:
            bad.append((name, longest))
    return bad
