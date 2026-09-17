# Attorney review request — CLOSED 2026-09-17

**Closed by Fred's ruling, 2026-09-17:** appeal letters rest on EVIDENCE AND ARGUMENT ONLY.
No legal language, no statutory or regulatory citation, no assertion about what a law
requires. If an appeal fails, escalation to an attorney is the user's judgment, informed by
the strength of the evidence and the value of the claim; the product may surface the facts
that bear on that judgment, never the judgment itself.

Consequence: the twelve Ohio candidate provisions were never going to be cited by the
product, so the request for an attorney to sign them is withdrawn. No review was
commissioned; nothing here was sent.

## What is kept here, as historical artifacts (do not delete)

| file | what | built |
|---|---|---|
| `CivicScale-Legal-Review-Request.docx` / `.pdf` | the review-request document, later build (2026-09-14 18:33) | `build_attorney_doc.js` |
| `../../Claude outputs/CivicScale-Legal-Review-Request.docx` | earlier build (2026-09-14 18:19); left where it was | same |
| `build_attorney_doc.js` | the docx builder (copy; the versioned one is `backend/scripts/legal_review/build_attorney_doc.js`) | — |
| `attorney_provisions.json` | the twelve provisions as sheets (id, denial code, citation, heading, source URL, verbatim excerpt, what the letter would assert). Same content as `backend/scripts/legal_review/provisions.json`, which `build_provisions.py` writes from `backend/data/verify/candidates.json` + fetched text. Note: `build_attorney_doc.js` does not read this JSON; its sheet text is embedded. | `build_provisions.py` |

## Related records now superseded by the ruling
- `docs/appeal-citation-candidates-review-2026-09.md` — the review packet (status note added at top).
- `docs/signal-phase3-frozen-sources-design.md` §intro — "the letter half of Phase 3 is blocked on the attorney review": no longer blocked; the letter half is re-scoped by the ruling.
- `backend/data/verify/candidates.json` — the twelve rows stay `reviewed_by: null`; under the ruling the allow-list is permanently empty. (Code and data untouched pending the APPEALS follow-up directive.)
- `backend/routers/health_analyze.py:653-658` — "LEGAL REVIEW PENDING" comment on the reservation-of-rights sentence; the sentence itself is legal language and is in the APPEALS-1 audit list.
