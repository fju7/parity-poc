#!/bin/bash
# Install the weekly lead scan as a launchd job. Run once, from anywhere:
#   bash backend/scripts/whatholdsup/schedule/install.sh
#
# The plist is GENERATED here rather than shipped, so the absolute path is
# whatever the repo's path actually is at install time. It was previously a
# static file with a Desktop path baked in, which stopped being true the moment
# the repo moved.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
LABEL="org.whatholdsup.leadscan"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

case "$REPO" in
  "$HOME/Desktop/"*|"$HOME/Documents/"*|"$HOME/Downloads/"*)
    echo
    echo "  REFUSING TO INSTALL."
    echo
    echo "  The repo is at:"
    echo "    $REPO"
    echo
    echo "  macOS protects Desktop, Documents and Downloads. A launchd agent"
    echo "  cannot read them, and the job will fail with:"
    echo "    /bin/bash: ...run_scan.sh: Operation not permitted"
    echo
    echo "  Move the repo somewhere unprotected and run this again:"
    echo "    mkdir -p \"\$HOME/Projects\""
    echo "    mv \"$REPO\" \"\$HOME/Projects/\""
    echo
    echo "  Then reconnect the folder in the Claude desktop app."
    echo
    exit 1 ;;
esac

mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$REPO/backend/scripts/whatholdsup/schedule/run_scan.sh</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Weekday</key><integer>1</integer>
    <key>Hour</key><integer>9</integer>
    <key>Minute</key><integer>0</integer>
  </dict>
  <key>RunAtLoad</key>
  <false/>
  <key>StandardOutPath</key>
  <string>/tmp/whatholdsup-leadscan.out</string>
  <key>StandardErrorPath</key>
  <string>/tmp/whatholdsup-leadscan.err</string>
</dict>
</plist>
PLISTEOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo
echo "  Installed for repo: $REPO"
echo "  Runs Mondays at 09:00 local."
echo "    run it now:   launchctl kickstart -k gui/$(id -u)/$LABEL"
echo "    see the log:  tail -n 60 \"$REPO/issues/leads/scan.log\""
echo "    errors:       cat /tmp/whatholdsup-leadscan.err"
echo "    remove it:    launchctl bootout gui/$(id -u)/$LABEL && rm \"$PLIST\""
