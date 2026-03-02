"""
Parity Signal: Pipeline Orchestrator.

Runs all seven pipeline steps in sequence with a single command:
  1. collect_sources.py          — Load sources into Supabase
  2. extract_claims.py           — Extract + deduplicate claims
  3. score_claims.py             — Score claims across 6 dimensions
  4. map_consensus.py            — Map consensus per category
  5. generate_summary.py         — Generate versioned summary
  6. detect_changes.py           — Detect evidence changes vs previous run
  7. generate_notifications.py   — Generate notifications for subscribers

Each step is run as a subprocess for clean isolation (each script manages
its own argparse, sys.exit, and state).

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    python scripts/signal/run_pipeline.py --dry-run
    python scripts/signal/run_pipeline.py --force
    python scripts/signal/run_pipeline.py --from 3 --force
    python scripts/signal/run_pipeline.py --from 3 --to 4 --force
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

STEPS = [
    {
        "num": 1,
        "name": "Collect Sources",
        "script": "collect_sources.py",
        "supports_force": False,
        "supports_dry_run": True,
    },
    {
        "num": 2,
        "name": "Extract Claims",
        "script": "extract_claims.py",
        "supports_force": True,
        "supports_dry_run": True,
    },
    {
        "num": 3,
        "name": "Score Claims",
        "script": "score_claims.py",
        "supports_force": True,
        "supports_dry_run": True,
    },
    {
        "num": 4,
        "name": "Map Consensus",
        "script": "map_consensus.py",
        "supports_force": True,
        "supports_dry_run": True,
    },
    {
        "num": 5,
        "name": "Generate Summary",
        "script": "generate_summary.py",
        "supports_force": False,
        "supports_dry_run": True,
    },
    {
        "num": 6,
        "name": "Detect Changes",
        "script": "detect_changes.py",
        "supports_force": True,
        "supports_dry_run": True,
    },
    {
        "num": 7,
        "name": "Generate Notifications",
        "script": "generate_notifications.py",
        "supports_force": False,
        "supports_dry_run": True,
    },
]


def build_command(step: dict, dry_run: bool, force: bool) -> list[str]:
    """Build the subprocess command for a pipeline step."""
    cmd = [sys.executable, str(SCRIPTS_DIR / step["script"])]

    if dry_run and step["supports_dry_run"]:
        cmd.append("--dry-run")

    if force and step["supports_force"]:
        cmd.append("--force")

    return cmd


def run_step(step: dict, dry_run: bool, force: bool) -> tuple[bool, float, str]:
    """Run one pipeline step as a subprocess.

    Returns (success, elapsed_seconds, output_text).
    """
    cmd = build_command(step, dry_run, force)
    start = time.time()

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(SCRIPTS_DIR.parent.parent),  # backend/
    )

    elapsed = time.time() - start
    output = result.stdout
    if result.stderr:
        output += result.stderr

    return result.returncode == 0, elapsed, output


def format_time(seconds: float) -> str:
    """Format seconds as human-readable duration."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.0f}s"


def main():
    parser = argparse.ArgumentParser(
        description="Run the full Parity Signal evidence pipeline."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Pass --dry-run to each step (no API calls, no DB writes)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Pass --force to steps 2-4 (clear and re-run)",
    )
    parser.add_argument(
        "--from",
        type=int,
        default=1,
        dest="from_step",
        metavar="STEP",
        help="Start from step N (1-7, default: 1)",
    )
    parser.add_argument(
        "--to",
        type=int,
        default=7,
        dest="to_step",
        metavar="STEP",
        help="Stop after step N (1-7, default: 7)",
    )
    args = parser.parse_args()

    # Validate step range
    if args.from_step < 1 or args.from_step > 7:
        print(f"ERROR: --from must be between 1 and 7 (got {args.from_step})")
        sys.exit(1)
    if args.to_step < 1 or args.to_step > 7:
        print(f"ERROR: --to must be between 1 and 7 (got {args.to_step})")
        sys.exit(1)
    if args.from_step > args.to_step:
        print(f"ERROR: --from ({args.from_step}) cannot be greater than --to ({args.to_step})")
        sys.exit(1)

    # Filter steps
    steps_to_run = [s for s in STEPS if args.from_step <= s["num"] <= args.to_step]

    mode = "DRY RUN" if args.dry_run else "LIVE"
    force_label = " (--force)" if args.force else ""
    step_range = f"steps {args.from_step}-{args.to_step}" if args.from_step != 1 or args.to_step != 7 else "all steps"

    print(f"{'='*60}")
    print(f"PARITY SIGNAL PIPELINE — {mode}{force_label}")
    print(f"Running {step_range}")
    print(f"{'='*60}\n")

    total_start = time.time()
    results = []

    for step in steps_to_run:
        num = step["num"]
        name = step["name"]
        print(f"[Step {num}/7] {name}")
        print(f"{'-'*40}")

        success, elapsed, output = run_step(step, args.dry_run, args.force)

        # Print output indented
        for line in output.strip().split("\n"):
            print(f"  {line}")

        if success:
            print(f"\n  -> Completed in {format_time(elapsed)}")
            results.append((num, name, "OK", elapsed))
        else:
            print(f"\n  -> FAILED after {format_time(elapsed)}")
            results.append((num, name, "FAILED", elapsed))
            print(f"\nPipeline stopped at step {num}. Fix the error and resume with --from {num}")
            break

        print()

    total_elapsed = time.time() - total_start

    # Summary
    print(f"{'='*60}")
    print(f"PIPELINE SUMMARY")
    print(f"{'='*60}")
    for num, name, status, elapsed in results:
        status_icon = "OK" if status == "OK" else "FAIL"
        print(f"  Step {num} {name:.<30s} {status_icon}  ({format_time(elapsed)})")
    print(f"  {'':.<38s}--------")
    print(f"  Total{'':.>32s}  {format_time(total_elapsed)}")

    failed = any(s == "FAILED" for _, _, s, _ in results)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
