# Queued jobs

Long work runs here instead of being pasted into a terminal.

## Why

Every shell the assistant opens on this Mac lives in a fresh container that is
destroyed when the call returns, with a hard 180-second ceiling. Verified on
2026-08-31: a detached `setsid nohup` loop writing a line a second stopped at
tick 3, exactly when the call ended, and the shell's own PID was 2 — a new PID
namespace per call. No permission setting changes that. A gate run takes
minutes, so it had to be copied into a terminal by hand and its output copied
back.

launchd runs outside that container and survives, which is what the weekly lead
scan already relies on.

## What it will run

**Only a `.py` file that already exists under `backend/scripts`, with
arguments.** Not arbitrary shell. Anything else is refused and the refusal is
written to the log.

That is narrower than it needs to be for convenience, on purpose. It removes
the copying without quietly becoming a general remote shell.

## What you are agreeing to

Worth being plain about, because it is a real change:

- Jobs run **unattended, as you**, with your `.env` and therefore your API key.
  They can spend money. The `$40`-an-issue cap in `backend/data/spend/caps.json`
  still applies, and every priced call still lands in the ledger.
- You no longer see each command before it runs. You see them **afterwards**:
  the job file, its full output and its exit code are all kept, and the queue
  lives in the repo where git shows you what appeared.

If you would rather keep approving each command, do not install it. The
copy-and-paste loop is slower but you are in it.

## Layout

    queue/   jobs waiting.  A job is claimed by moving it to done/ before it
             runs, so a second launchd tick cannot start it twice and spend twice.
    logs/    <job>.log — the job file, then everything it printed.
    done/    <job>.json and <job>.exit (the exit code).

## Install once

    bash backend/scripts/whatholdsup/schedule/install_runner.sh

Stop it any time:

    launchctl unload ~/Library/LaunchAgents/org.whatholdsup.jobrunner.plist
