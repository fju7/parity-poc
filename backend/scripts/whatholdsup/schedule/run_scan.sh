#!/bin/bash
# What Holds Up — weekly lead scan.
#
# Runs on this Mac, on a schedule, with no Claude session involved. That is
# deliberate: the scan is deterministic data collection and needs no model. The
# model work is the funnel, which happens afterwards when a person looks at
# what the scan found.
#
# It also has to run here because both data sources are unreachable from the
# assistant's cloud container -- GDELT's robots.txt cannot be fetched from
# there and the Wikimedia REST API is cache-only.
set -uo pipefail

REPO="/Users/fredugast/Desktop/AI Projects/Parity Medical/parity-poc-repo"
cd "$REPO" || { echo "repo not found at $REPO"; exit 1; }

LOG="$REPO/issues/leads/scan.log"
mkdir -p "$REPO/issues/leads"

# Query sets rotate by week of year, so consecutive runs look at different
# ground. Re-measuring one list every week tells you how one list is doing; the
# point is to notice what is newly live.
WEEK=$(date +%V)
case $(( 10#$WEEK % 4 )) in
  0) QUERIES=( '"clinical trial" results announced' 'FDA approval evidence' '"peer reviewed" study findings contradict' ) ;;
  1) QUERIES=( 'settlement lawsuit "does not admit"' 'class action evidence allegations' 'regulator fine investigation findings' ) ;;
  2) QUERIES=( 'study finds link causes' '"new research" shows risk' 'report warns evidence' ) ;;
  *) QUERIES=( 'government data revised figures' 'audit report findings agency' 'economists dispute estimate' ) ;;
esac

{
  echo "=============================================================="
  echo "scan $(date -u +%Y-%m-%dT%H:%M:%SZ)  week $WEEK  set $(( 10#$WEEK % 4 ))"
  /usr/bin/python3 backend/scripts/whatholdsup/scan_leads.py scan "${QUERIES[@]}" --timespan 14d
  echo "exit=$?"
} >> "$LOG" 2>&1

# Keep the log from growing without bound.
tail -n 2000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
