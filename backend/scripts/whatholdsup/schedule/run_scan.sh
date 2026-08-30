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

# Derive the repo from this script's own location rather than hardcoding it.
# The path was hardcoded to a Desktop folder, which broke twice over: once when
# the repo needed to move out of macOS's protected directories, and once
# because a hardcoded path is a thing that has to be found and changed in three
# files every time anything moves.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
cd "$REPO" || { echo "repo not found from $HERE"; exit 1; }
if [ ! -f "backend/scripts/whatholdsup/scan_leads.py" ]; then
  echo "this does not look like the repo: $REPO"; exit 1
fi

LOG="$REPO/issues/leads/scan.log"
mkdir -p "$REPO/issues/leads"

# Query sets rotate by week of year, so consecutive runs look at different
# ground. Re-measuring one list every week tells you how one list is doing; the
# point is to notice what is newly live.
#
# Rewritten 2026-08-29 for the belief test. The old sets asked what is being
# covered. These ask what is being SETTLED -- the headline shapes that turn a
# finding into a confident public belief:
#
#   "linked to"        the canonical correlation-reported-as-cause construction
#   "could be" / "may" hedged in the paper, unhedged by the time it is carried
#   "proves" / "shows" certainty asserted about something rarely certain
#   "no evidence"      a universal negative, which is the claim most often wrong
#   "debunked"         a correction that may itself be overstated
#
# The last of those matters for the contrarianism guard: a subject where the
# common belief turns out to be RIGHT is one we are overdue to publish, and
# "debunked" headlines are where those live.
WEEK=$(date +%V)
case $(( 10#$WEEK % 4 )) in
  # 2026-08-30: the contrarianism guard fired at four issues with no
  # confirmation, and asked whether our selection was picking for the answer.
  # It was, and the evidence was here. Three of the four sets hunted the shape
  # of an OVERSTATED claim -- "linked to", "proves", "may cause" -- and only
  # one hunted the shape of an overstated DEBUNKING, which is where an issue
  # confirming a widely held belief would come from. Three to one against ever
  # finding one. Nobody chose that; a query for an inflated claim is simply
  # easier to write than a query for a belief that turns out to be right.
  #
  # Set 1 now takes half the rotation. This does not manufacture a
  # confirmation. It stops the instrument making one three times less likely.
  1|3) QUERIES=( '"no evidence" study claim' '"debunked" study researchers' '"myth" experts say' \
                 '"turns out to be true" study' '"was right all along" research' ) ;;
  0) QUERIES=( '"linked to" study children' '"linked to" study risk' '"study finds" causes' ) ;;
  2) QUERIES=( '"proves" study researchers' '"shows that" new research' '"first time" study demonstrates' ) ;;
  *) QUERIES=( '"could increase" study' '"may cause" research suggests' '"raises risk" study finds' ) ;;
esac

{
  echo "=============================================================="
  echo "scan $(date -u +%Y-%m-%dT%H:%M:%SZ)  week $WEEK  set $(( 10#$WEEK % 4 ))"
  /usr/bin/python3 -u backend/scripts/whatholdsup/scan_leads.py scan "${QUERIES[@]}" --timespan 14d
  echo "exit=$?"
} >> "$LOG" 2>&1

# ---------------------------------------------------------------------------
# The source sweeps. Added 2026-08-30, after an outside reviewer found a
# prospective trial we had said did not exist -- Pedersen et al., in print
# since 3 June 2026, citing our central study, with that study's senior author
# on it -- and after we discovered a correction to that same central study that
# had been sitting in PubMed since 11 September 2025.
#
# The scan above watches ATTENTION: GDELT and Wikipedia, what is being
# published and read. That is how a SUBJECT is found. It is not how a subject
# already published is watched, and nothing we owned did that. These two do,
# for free, against Europe PMC.
#
# Every issue with a sources.json is swept, so a page does not fall off the
# watch because nobody remembered it.
for SRC in "$REPO"/issues/*/sources.json; do
  [ -e "$SRC" ] || continue
  SLUG="$(basename "$(dirname "$SRC")")"
  {
    echo "--------------------------------------------------------------"
    echo "sweep $(date -u +%Y-%m-%dT%H:%M:%SZ)  $SLUG"
    /usr/bin/python3 -u "$REPO/backend/scripts/whatholdsup/sweep_sources.py" status "$SLUG" --quiet
    /usr/bin/python3 -u "$REPO/backend/scripts/whatholdsup/sweep_sources.py" citations "$SLUG"
    echo "exit=$?"
  } >> "$LOG" 2>&1
done

# Keep the log from growing without bound.
tail -n 2000 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
