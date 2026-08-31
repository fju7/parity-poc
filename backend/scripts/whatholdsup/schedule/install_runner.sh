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

# logs/ must exist BEFORE launchd loads this, not when runner.sh gets around
# to creating it. launchd opens StandardOutPath and StandardErrorPath at SPAWN;
# if the directory is missing it cannot, and the first install left logs/
# absent while pointing both redirects into it.
mkdir -p "$HOME/Library/LaunchAgents" \
         "$REPO/backend/data/jobs/queue" \
         "$REPO/backend/data/jobs/logs" \
         "$REPO/backend/data/jobs/done"
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
launchctl load "$PLIST" 2>/dev/null || true

# VERIFY, rather than announce. The first install printed "installed" and the
# agent never ran once: no runner.out, no runner.err, a job sitting in the
# queue for minutes. `launchctl load` succeeding says the file parsed, not that
# the job is registered, and on recent macOS `load` is deprecated in favour of
# `bootstrap`. An installer that reports success it has not checked is the same
# defect as a gate that reports a pass it did not run.
if ! launchctl list | grep -q "$LABEL"; then
    echo "  'launchctl load' did not register the job; trying bootstrap..."
    launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || true
fi

if launchctl list | grep -q "$LABEL"; then
    echo
    echo "  REGISTERED: $LABEL"

    # A REGISTERED AGENT IS NOT AN AGENT THAT RUNS.
    #
    # This installer reported success twice for an agent that never executed a
    # job. The second version verified registration -- and on 2026-08-31
    # `launchctl list org.whatholdsup.jobrunner` returned a full record with
    # LastExitStatus 0 while logs/ was empty and two gate runs had sat unstarted
    # in the queue for an hour. Registered and working are different states and
    # the check could not tell them apart.
    #
    # So: queue a job that does nothing, and wait for the runner to eat it. If
    # it is gone and its exit code is on disk, the runner works, because it just
    # worked. Anything else is a failed install, whatever launchctl says.
    CANARY="$REPO/backend/data/jobs/queue/000-canary.json"
    cat > "$CANARY" <<'CANARY_END'
{
  "note": "Queued by install_runner.sh to prove the runner runs jobs. Prints and exits; reads nothing, writes nothing, spends nothing. If this file is still in the queue, the install failed.",
  "cwd": "backend",
  "script": "scripts/whatholdsup/schedule/canary.py",
  "args": []
}
CANARY_END
    echo "  waiting up to 90s for the runner to pick up a canary job..."
    ok=""
    for _ in $(seq 1 18); do
        sleep 5
        if [ -f "$REPO/backend/data/jobs/done/000-canary.exit" ]; then ok="yes"; break; fi
    done
    if [ -n "$ok" ]; then
        echo "  VERIFIED — the runner executed a queued job:"
        sed -n 's/^/      /p' "$REPO/backend/data/jobs/logs/000-canary.log" 2>/dev/null | tail -4
    else
        echo
        echo "  NOT WORKING. The agent is registered and did not run a job in 90"
        echo "  seconds, with StartInterval set to 30. The canary is still at:"
        echo "      $CANARY"
        echo "  Anything queued here will sit unstarted. Look at:"
        echo "      launchctl list $LABEL"
        echo "      cat $REPO/backend/data/jobs/logs/runner.err"
        echo "  and run the queue by hand meanwhile:"
        echo "      bash $REPO/backend/scripts/whatholdsup/schedule/runner.sh"
        exit 1
    fi
else
    echo
    echo "  NOT REGISTERED. The plist is written at $PLIST but launchd has not"
    echo "  accepted it, so nothing will run. Try:"
    echo "      launchctl bootstrap gui/\$(id -u) $PLIST"
    echo "      launchctl list | grep $LABEL"
    exit 1
fi

# macOS ships bash 3.2 and the plist calls /bin/bash. runner.sh is written for
# 3.2 deliberately; this notices if that ever stops being true.
echo "  /bin/bash is $(/bin/bash --version | head -1 | sed 's/.*version //;s/ .*//')"
echo
echo "  installed: $PLIST"
echo "  it checks $REPO/backend/data/jobs/queue every 30 seconds"
echo
echo "  Check it is alive:"
echo "    launchctl list | grep $LABEL"
echo "  Stop it, any time:"
echo "    launchctl unload $PLIST"
echo
