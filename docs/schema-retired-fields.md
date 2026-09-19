# Schema — retired fields

One row per column that has been retired or renamed. A column listed here must not be read by new
code; the migration that comments or renames it is named so the database says the same thing the
repo does. Data is never dropped by the retirement itself; whether the rows still exist is stated.

| column | date retired | commit | why | data still exists? | migration |
|---|---|---|---|---|---|
| `provider_appeals.appeal_strength` | 2026-09-19 | `e679913` (APPEALS-4) | The model-authored letter grade high\|medium\|low asked the model for the user's judgment and asserted an outcome relation nothing examined. Every writer, reader and renderer removed. | **Yes** — rows written before 2026-09-19 keep their values; they are the record of what was once asserted to (test) users. Must not be read. | `094_provider_appeals_appeal_strength_retired_comment.sql` — `COMMENT ON COLUMN` (written 2026-09-19, **unapplied** until Fred applies it) |
| `signal_denial_playbook.appeal_strength` → **renamed** `signal_claim_count_band` | 2026-09-19 (code: `032a629`, APPEALS-5; column: when 093 is applied) | `032a629` | Not the letter grade: a band of how many Signal claims map to the CPT's topic (≥3 / 1–2 / 0). The name asserted appeal strength; the procedure measured claim count. Values restated as `3_plus_claims` / `1_2_claims` / `0_claims`. | **Yes** — the rows persist under the new name after 093 (values remapped in the same migration). Reached no user: nothing renders `signal_evidence` and no caller of `/api/signal/denial-intelligence` exists. | `093_signal_denial_playbook_claim_count_band.sql` — rename + remap + CHECK + COMMENT (written 2026-09-19, **unapplied**; apply BEFORE code that reads the new name is served — that code is live since `032a629`, see appeals-record) |

Guard: `backend/tests/test_appeals5.py::test_no_code_file_uses_the_name_appeal_strength` fails if the name
`appeal_strength` (the retired column's name) appears in any non-comment line of backend or frontend code
outside the migrations and this document.
