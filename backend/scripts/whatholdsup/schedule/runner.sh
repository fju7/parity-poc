#!/bin/bash
# Run queued repo jobs, so long work does not need a person at the keyboard.
#
# WHY THIS EXISTS
# ---------------
# Every shell the assistant opens on this Mac runs in a fresh container that is
# destroyed the moment the call returns, with a hard 180-second ceiling.
# Verified on 2026-08-31: a `setsid nohup ... &` loop writing one line a second
# stopped at tick 3, exactly when the call ended, and the shell's own PID was 2
# — a new PID namespace per call. No permission changes this. A gate run takes
# minutes, so every one of them had to be copied into a terminal by hand and
# its output copied back.
#
# launchd runs outside that container, as the user, and survives. This is the
# same mechanism the weekly lead scan already uses.
#
# WHAT IT WILL AND WILL NOT RUN
# -----------------------------
# Only a Python file that already lives under backend/scripts, with arguments.
# NOT arbitrary shell. The queue is inside the repo, so every job is a file you
# can read before it runs and git can show you afterwards. Job text, exit code
# and full output are archived.
#
# That is deliberately narrower than it could be. It removes the copying, and
# it does not quietly turn into a general remote shell.
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
JOBS="$REPO/backend/data/jobs"
PY="$REPO/backend/venv/bin/python3"

mkdir -p "$JOBS/queue" "$JOBS/logs" "$JOBS/done"
[ -x "$PY" ] || { echo "no venv python at $PY" >&2; exit 1; }

shopt -s nullglob
for job in "$JOBS"/queue/*.json; do
  name="$(basename "$job" .json)"
  log="$JOBS/logs/$name.log"

  # Claim it by moving it out of the queue first: launchd may fire again while
  # a long job is still running, and a job started twice would spend twice.
  claimed="$JOBS/done/$name.json"
  mv "$job" "$claimed" 2>/dev/null || continue

  script="$("$PY" -c "import json,sys;print(json.load(open(sys.argv[1])).get('script',''))" "$claimed" 2>/dev/null)"
  cwd="$("$PY" -c "import json,sys;print(json.load(open(sys.argv[1])).get('cwd','backend'))" "$claimed" 2>/dev/null)"

  {
    echo "=== $name"
    echo "=== queued job:"
    cat "$claimed"
    echo "=== started $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } > "$log"

  # The script must be a .py under backend/scripts. Anything else is refused
  # and recorded, rather than run because it was asked for.
  case "$script" in
    scripts/*.py|scripts/*/*.py) ;;
    *) echo "REFUSED: '$script' is not a .py under backend/scripts" >> "$log"
       echo "127" > "$JOBS/done/$name.exit"; continue ;;
  esac
  if [ ! -f "$REPO/backend/$script" ]; then
    echo "REFUSED: $REPO/backend/$script does not exist" >> "$log"
    echo "127" > "$JOBS/done/$name.exit"; continue
  fi

  # NOT mapfile: macOS ships bash 3.2 and mapfile arrived in bash 4. The plist
  # calls /bin/bash, so this script has to run on 3.2 or it does not run at
  # all. Read the args with a while-read loop instead, NUL-free and portable.
  args=()
  while IFS= read -r a; do
    args+=("$a")
  done < <("$PY" -c "import json,sys;[print(a) for a in json.load(open(sys.argv[1])).get('args',[])]" "$claimed" 2>/dev/null)

  cd "$REPO/$cwd" || { echo "no such cwd: $cwd" >> "$log"; echo "127" > "$JOBS/done/$name.exit"; continue; }
  "$PY" "$REPO/backend/$script" ${args[@]+"${args[@]}"} >> "$log" 2>&1
  code=$?
  echo "$code" > "$JOBS/done/$name.exit"
  echo "=== finished $(date -u +%Y-%m-%dT%H:%M:%SZ) exit=$code" >> "$log"
done
