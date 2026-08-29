#!/bin/bash
# Install the weekly lead scan as a launchd job. Run once:
#   bash backend/scripts/whatholdsup/schedule/install.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PLIST="$HOME/Library/LaunchAgents/org.whatholdsup.leadscan.plist"

mkdir -p "$HOME/Library/LaunchAgents"
cp "$HERE/org.whatholdsup.leadscan.plist" "$PLIST"

launchctl bootout "gui/$(id -u)/org.whatholdsup.leadscan" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo
echo "Installed. It runs Mondays at 09:00 local."
echo "  run it now:   launchctl kickstart -k gui/$(id -u)/org.whatholdsup.leadscan"
echo "  see the log:  tail -n 60 'issues/leads/scan.log'"
echo "  remove it:    launchctl bootout gui/$(id -u)/org.whatholdsup.leadscan && rm '$PLIST'"
