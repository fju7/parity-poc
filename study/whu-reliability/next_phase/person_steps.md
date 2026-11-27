# Steps that still need a person under lean (advisor's ruling 3 on P169, 2026-11-27)

This list comes from reading the code at P172; updated at P182 (advisor's ruling 4 on P171-P176). Recency findings are no longer on it. A recency finding with no body
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

## What went to a person, and what code does now (advisor's ruling 4 on P171-P176, 2026-11-27; P182)

Under lean none of these goes to a person any more. Each ends in an automatic, fail-safe outcome. Outside lean
every path is unchanged.

| Where | When | Lean outcome now |
|---|---|---|
| `acquire_sources.py` | A source whose licence forbids machine reading. | Refused and recorded: `access.refused` {why, on, by} in sources.json; never fetched, so never held or cited. |
| `audit_stage.py` (licence branch) | A page sentence bound only to licence-barred sources. | The sentence is withheld: `must_leave_page`, a lean fail-safe record (path `audit`), and the orchestrator's apply removes it. |
| `audit_stage.py` (FAILED_READ) | An audit read that failed. | The sentence is withheld, as above. No `human_reads.jsonl` is needed. |
| `ruling.py` omissions (licence) | An omission objection on a licence-barred source. | Refused and recorded: `REFUSED_LICENCE` in omissions.json. Not ruled, not open, and nothing added. |
| `ruling.py` omissions (unusable reply) | The omission ruling's reply was not usable after its re-ask. | The finding goes onto the readers' list as declared: `DECLARED_UNRULED`, the line "Not added: ... (our ruling on it could not be completed).", counted against the declarations budget. |
| `ruling.py` omissions (scope) | OUT_OF_SCOPE names a scope element code cannot find in the question or scope.out. | The declaration stands as OUT_OF_SCOPE with no element and counts against the budget. It is never exempt. |
| `ruling.py` omissions (budget) | A declaration past the declarations budget (min(10, 20% of body sentences)). | Not Ready, an honest stop: `OVER_DECLARATIONS_BUDGET`. The orchestrator ends the run at the omissions step, before any later step spends, and the row "omission objections ruled" STOPs with "Not Ready". |
| `ruling.py` omissions (serious) | NOT_MATERIAL ruled on a SERIOUS objection that CHANGES the conclusion. | Not accepted from the machine. The conclusion sentence the objection is about is withdrawn (path `omissions`) and nothing is declared. If that sentence cannot be withdrawn (it is protected, code-written, a required line, or not on the page), the page is Not Ready (`OVER_DECLARATIONS_BUDGET`, with the reason recorded). |
| `findings.py` "attested" | A gate finding on a licence-barred source. | No person step remains. Under lean a licence-barred source is refused at acquire, so no page sentence rests on it, and a gate finding about its claim is ruled by `ruling.py gate` like any other. The attestation path only closes a finding automatically when an operator answer already exists; it never routes one to a person. |

Tests: `backend/tests/test_whu_person_steps_automatic.py`. The serious-objection case is tested on its own
(withdrawn through apply; a protected anchor is Not Ready; NARROWS still declared as before).

Nothing on the list could not be automated.

## Settled: what the recency lines rest on (advisor's ruling 2 on P171-P176; P178)

"A newer edition exists of ..." is written only when a registry record shows the newer edition (errata.json: Europe
PMC / PubMed "Update in", Crossref "is-replaced-by", or a Crossref updated-by of type new_edition / new_version) or
the newer work is held. Otherwise the line uses the "Our recency check (searched: ...) could not establish whether ...
has a newer edition." wording. A gate web-search result alone never supports the line, and the preflight row
"newer editions handled" STOPs a recorded line that rests on it.
