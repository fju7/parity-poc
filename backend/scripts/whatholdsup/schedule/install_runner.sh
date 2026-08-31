#!/bin/bash
# Install the job runner as a launchd agent. Run ONCE:
#   bash backend/scripts/whatholdsup/schedule/install_runner.sh
#
# After this, long jobs (a gate run, a sweep) can be queued as files in
# backend/data/jobs/queue and will run without anyone at the keyboard. See
# runner.sh for what it will and will not execute.
#
# To stop it, ever:
#   launchctl unload ~/Library/LaunchAgents/org.whatholdsup.jobrunner.plist
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
LABEL="org.whatholdsup.jobrunner"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

# Same refusal as the lead scan, for the same reason: launchd agents cannot
# read Desktop, Documents or Downloads, and fail with "Operation not permitted"
# every time instead of saying so once.
case "$REPO" in
  "$HOME/Desktop/"*|"$HOME/Documents/"*|"$HOME/Downloads/"*)
    echo
    echo "  REFUSING TO INSTALL — the repo is at:"
    echo "    $REPO"
    echo "  macOS protects Desktop, Documents and Downloads; a launchd agent"
    echo "  cannot read them. Move the repo and run this again."
    echo
    exit 1 ;;
esac

[ -x "$REPO/backend/venv/bin/python3" ] || {
  echo "  No venv at $REPO/backend/venv — install dependencies first."; exit 1; }

mkdir -p "$HOME/Library/LaunchAgents" "$REPO/backend/data/jobs/queue"
cat > "$PLIST" <<PLIST_END
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$REPO/backend/scripts/whatholdsup/schedule/runner.sh</string>
  </array>
  <key>StartInterval</key><integer>30</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$REPO/backend/data/jobs/logs/runner.out</string>
  <key>StandardErrorPath</key><string>$REPO/backend/data/jobs/logs/runner.err</string>
  <key>WorkingDirectory</key><string>$REPO</string>
</dict>
</plist>
PLIST_END

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo
echo "  installed: $PLIST"
echo "  it checks $REPO/backend/data/jobs/queue every 30 seconds"
echo
echo "  Check it is alive:"
echo "    launchctl list | grep $LABEL"
echo "  Stop it, any time:"
echo "    launchctl unload $PLIST"
echo
