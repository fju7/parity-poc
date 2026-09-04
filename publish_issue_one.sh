#!/bin/bash
# Publish and announce issue one (melanoma), 4 September 2026.
#
# Why a script and not two commands:
#
#   1. `python` is not on the PATH on macOS and the repo's dependencies
#      (resend, anthropic, dotenv) live in backend/venv, not in the system
#      interpreter. Both commands need backend/venv/bin/python.
#
#   2. git creates .git/index.lock on every write and removes it after. The
#      bridge from the cloud session to this machine blocks deletes, so a lock
#      left by the session's last git call makes the next one fail. Run from
#      your own terminal, where git cleans up after itself, and clear any lock
#      the session left behind first. Same reason as publish_issue_two.sh.
#
#   3. announce refuses while the live site is older than the repo -- the email
#      links to the page and vouches for it. So publish must finish, and the
#      deploy must land, before announce runs. Doing it in one script keeps
#      that order.
#
# Run:  bash publish_issue_one.sh
#
# It stops at the first failure. Nothing is sent unless the publish succeeded
# and every preflight check passed: there is no --waive here, and the announce
# path will not accept one on the page gate in any case.

set -euo pipefail
cd "$(dirname "$0")"
rm -f .git/index.lock .git/HEAD.lock

PY="backend/venv/bin/python"
[ -x "$PY" ] || { echo "no interpreter at $PY"; exit 1; }

echo "=============================================================="
echo "Branch: $(git rev-parse --abbrev-ref HEAD)   (the host deploys main)"
echo "Head:   $(git log --oneline -1)"
echo "=============================================================="
echo

echo "--- 1/2  publish: preflight, commit, push, wait for the deploy ---"
"$PY" backend/scripts/whatholdsup/publish.py publish melanoma --yes
rm -f .git/index.lock .git/HEAD.lock

echo
echo "--- 2/2  announce: preflight the email, then send ---"
"$PY" backend/scripts/whatholdsup/publish.py announce melanoma --yes
rm -f .git/index.lock .git/HEAD.lock

echo
echo "Done. Record: backend/data/whatholdsup/published.json"
