# Steps that still need a person under lean (advisor's ruling 3 on P169, 2026-11-27)

This list comes from reading the code at P172. Recency findings are no longer on it. A recency finding with no body
sentence to rule on is settled by code:

- `ruling.py gate` → `lean_editions_gate` → `lean_editions.decide`.
- A held source the finding names by identifier, author and title, or title gets its line on the page: either "A
  newer edition exists of …; this page uses …" or "Our recency check (searched: …) could not establish whether …".
- A finding tied to no held source is recorded and counted on the page.
- On 01d, the WHO guideline (rec-6) is tied to S006 by its URL, and Marcolino 2018 (rec-7), not held, is counted.
  See `backend/tests/test_whu_recency_machine_led.py`.

In lean, protected sentences are never sent to a person. A generated sentence is checked against its records. A
hand-written protected sentence must leave the page (`audit_stage.py`, lean branch). Items left for a person for
the reasons question, reading, scope or ambiguous are taken by the fail-safe (`lean_failsafe.REMOVABLE`).

## What still goes to a person, and stops a lean run

| Where | When | Why a person |
|---|---|---|
| `audit_stage.py:1355` | A page sentence bound only to sources whose licence forbids machine reading. | No model may read the source, so HUMAN_READ_REQUIRED. |
| `audit_stage.py:1537` | An audit read that failed (FAILED_READ). | HUMAN_READ_REQUIRED. The preflight blocks until `human_reads.jsonl` records the read. |
| `ruling.py:1361` | An omission objection on a licensed source. | The same licence bar. |
| `ruling.py:1437` | The omission ruling's reply was not usable after its re-ask. | `TO_PERSON`. Not a fail-safe reason. |
| `ruling.py:1444` | OUT_OF_SCOPE names a scope element code cannot find in the question or scope.out. | Code refused the model's element. |
| `ruling.py:1447`, `:1462` | A declaration past the declarations budget (min(10, 20% of body sentences)). | Fix 2 ruling 3: past the budget goes to a person. Under lean, the coverage rows STOP on it anyway. |
| `ruling.py:1459` | NOT_MATERIAL ruled on a SERIOUS objection that CHANGES the conclusion. | Code refuses the dismissal. |
| `findings.py` "attested" | A gate finding on a licence-barred source is closed only by an operator's recorded answer. | Only the operator holds the source. |

## Open: what the recency lines rest on

Ruling 3 asks that a newer-edition line be bound to the registry record, or recorded as unchecked when the newer
work is not held.

- The UNKNOWN line names the registries the recency check searched. A record with no list STOPs the row "newer
  editions handled".
- The SUPERSEDED line ("A newer edition exists of …") rests on the gate's recency record, which is a model's web
  search, not on a registry record.

Binding that line to a registry record, or marking it unchecked, would change what the line rests on. That is a
change to a check's meaning, so it is reported to the advisor and not built.
