#!/usr/bin/env python3
"""A job that exists to prove the runner runs jobs.

WHY THIS EXISTS
---------------
install_runner.sh has now reported success twice for an agent that has never
executed a single job. The first version announced "installed" without checking
anything. The second learned to VERIFY -- and verified the wrong thing:

    if launchctl list | grep -q "$LABEL"; then echo "REGISTERED and verified"

That checks the job is REGISTERED. On 2026-08-31 `launchctl list
org.whatholdsup.jobrunner` returned a full record with LastExitStatus 0, and
backend/data/jobs/logs/ was empty, and two gate runs had sat unstarted in the
queue for an hour. Registered and working are different states, and the
installer could not tell them apart.

That is the same defect this whole repository keeps finding in itself. The gate
learned that an unrun check is not a pass. source_ledger learned that an unread
source is not a source that agrees with us. registry_facts learned that an
absence reported by a retrieval that failed is not an absence. This is the
installer's turn: A REGISTERED AGENT IS NOT AN AGENT THAT RUNS.

So the installer now queues this file and waits for the runner to eat it. If
the job is gone from the queue and its exit code is on disk, the runner works,
because it just worked. If it is still sitting there, the install failed and
says so, whatever launchctl claims.

It prints and exits. It reads nothing, writes nothing, and spends nothing.
"""
import sys
from datetime import datetime, timezone

print("canary: the runner executed a queued job at %s"
      % datetime.now(timezone.utc).isoformat(timespec="seconds"))
print("canary: python is %s" % sys.executable)
sys.exit(0)
