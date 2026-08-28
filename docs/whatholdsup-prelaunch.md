# What Holds Up — pre-launch checklist and build plan

Written 2026-08-27. Every "today" statement below was verified against the
running system on that date — the database, the DNS, the live site, the code —
not against documentation, which in several places disagrees with the system.

---

## Part 0 — What is actually true today

### The publication

| | State | Evidence |
|---|---|---|
| Issue one (melanoma) | Written, corrected, **not re-gated since the last edits** | `issue1-melanoma.html.gate.json` predates three edits |
| Issue one, live | **Stale.** The deployed page still reads "157 unblinded patients" | `curl https://whatholdsup.org/melanoma` |
| Issue two (CDK4/6) | Brief complete, four open questions resolved, **not drafted** | `docs/whatholdsup-issue2-inquiry.md` |
| Issue three (social media) | Corpus only — 47 claims, 6 propositions, no brief | `data/signal/mosaic_social-media-*.json` |
| The gate | 13 of 14 seeded errors found, last run | `factcheck_recall.py` |

### The site

| | State |
|---|---|
| `/`, `/melanoma`, `/who-pays-for-this` | Live, 200 |
| `/what-this-is` | Written today, **not deployed** |
| Signup form | Written today, **not deployed**; `/api/subscribe` returns 404 |
| Unsubscribe endpoint | Written, **never tested against a live request** |
| Homepage | Serves prospects only; nothing for a returning subscriber |
| Issue archive | The "Latest" list holds one entry and is hand-edited |
| Gate coverage of our own pages | **None.** `index`, `what-this-is` and `who-pays-for-this` have never been checked |

### Email

| | State |
|---|---|
| SPF | Present |
| DMARC | Present, `p=quarantine` |
| DKIM (Resend) | Present, `resend._domainkey` |
| MX | Google Workspace |
| Audience | `bae12ea6-cbad-4b91-b250-81991bf6b4b5`, 2 contacts, 1 already unsubscribed |
| Welcome email | **Does not exist.** A new subscriber receives nothing until the next issue |
| Double opt-in | **None.** Anyone can subscribe any address |

### The changelog — the part that is furthest from working

| | State |
|---|---|
| Scheduled | **No.** No workflow, no cron, no job. It runs when a human types the command |
| Times it has ever detected anything | **Two**, both on 2026-08-27, both `consensus_change` |
| Topics with a usable baseline | **2 of 9.** Seven have a single snapshot; detection needs two |
| Change text | `change_description` is `None` on both rows that exist |
| Alerting | **None.** `generate_notifications.py` writes rows; its own docstring says delivery "is NOT handled here" |
| Notification rows written | 10, none delivered to anyone |
| Coverage of published issues | **Zero.** The nine watched slugs are Signal topics. There is no melanoma topic |
| Subscriber model | Two of them: Supabase users for Signal, a Resend audience for What Holds Up. No join |
| `whatholdsup_unsubscribes` table | **Does not exist.** Migration 076 was never applied |

**The structural problem, stated once.** The detector watches a claim corpus for
score and consensus shifts. What will actually move on issue one is
INTerpath-001 releasing its numbers at a medical meeting — a *new primary
document*, not a shift inside a corpus we already hold. And issue one is not in
any corpus the detector watches. Scheduling the existing script more often does
not fix either half of that.

---

## Part 1 — The decision that gates the rest

**How does "subscribers see the changelog first" work?**

The recommendation is **public but delayed**: a `/changelog` page anyone can
read, where each entry appears publicly N days after it went to subscribers.
The advantage sold is time, not access. It needs no accounts, no sessions and
no paywall, the archive accrues for search, and a prospect can see exactly what
they would be getting.

The alternative is **subscriber accounts** — real logins and a gated changelog.
It is the only option that supports paid tiers later, and it is honest and
unambiguous. It costs auth, password reset, session handling, and a join
between the Resend list and Supabase users that does not exist today.

This is a product decision, not a technical one, and every item in Phase 3
below depends on which way it goes. **Nothing else is blocked by it** — Phases
0 to 2 are identical either way, which is why they come first.

---

## Part 2 — The checklist

`[F]` = needs Fred (API key, Supabase SQL editor, Vercel, DNS, send button).

### Phase 0 — Publish issue one

Now driven by `backend/scripts/whatholdsup/publish.py`, which will not let most
of these be skipped.

- [x] `[F]` Apply migration 076 — done 2026-08-28, verified by insert and delete
- [ ] `[F]` Re-run the gate on the email
- [ ] `[F]` Run the gate on `melanoma.html` — **it has never been gated at all**
- [ ] Resolve or record every finding
- [ ] `publish.py check melanoma` comes back clean
- [ ] `[F]` `publish.py publish melanoma --yes` — commits, pushes, waits for the
      deploy to actually serve it, and records it
- [ ] `[F]` Deploy the subscribe endpoint with the same push. Once the corrected
      issue is live and shareable, a reader who wants more has nowhere to go
- [ ] `[F]` Send the broadcast, then `publish.py announce melanoma --yes`
- [ ] Verify: arrives, renders, unsubscribe link resolves, row lands in
      `whatholdsup_unsubscribes`

### Phase 1 — Subscription works end to end

- [ ] `[F]` Set `RESEND_WHATHOLDSUP_AUDIENCE_ID=bae12ea6-cbad-4b91-b250-81991bf6b4b5` in Vercel
- [ ] `[F]` Confirm `UNSUBSCRIBE_SECRET`, `RESEND_WHATHOLDSUP_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` are set in Vercel
- [ ] `[F]` Test the real signup path with a real address
- [ ] `[F]` Confirm RLS on `whatholdsup_unsubscribes` refuses the anon key. There is no
      `SUPABASE_ANON_KEY` in `backend/.env`, so this could not be tested from here, and
      the table holds email addresses
- [ ] `[F]` Test the unsubscribe happy path: link → 200 → row in Supabase with `propagated_to_resend`
- [ ] Build the **welcome email**. Today a new subscriber gets silence until the next issue, which is when most lists lose people
- [ ] Decide on **double opt-in**. Today anyone can subscribe any address. Not required at this size; required before any paid tier
- [ ] Build the **Resend webhook** so unsubscribes made in Resend's own footer reach `whatholdsup_unsubscribes`. Without it that table is a partial record and cannot be the system of truth
- [ ] Run the gate over `index.html`, `what-this-is.html`, `who-pays-for-this.html`. Our own pages make claims and none has ever been checked
- [ ] Decide whether to publish the gate reports. `.vercelignore` now excludes them
      after `whatholdsup.org/email/send_broadcast.py` was found returning 200. Publishing
      the full record of every objection raised and rejected may be the most honest thing
      on the site — but it needs a page built for it, not a JSON file at a guessable URL
- [ ] Let a decision hold more than one ground. `draft_decisions.json` keys on
      `(draft, role, quote)`, so a second objection to a sentence that already has a
      decision is silently dropped on write. Happened once on 2026-08-28

### Phase 2 — Publish issue two, and make the site hold more than one issue

- [ ] Confirm the NCCN category ratings against NCCN itself. Currently a secondary summary, and the section collapses if it is wrong
- [ ] Source or drop the corpus's PALOMA-3 `p = 0.0221`. It matches neither published figure
- [ ] SOURCE-verify the PALOMA-2 figures
- [ ] Write the page and the email
- [ ] `[F]` Gate to exit 0, then read against every rule in the editorial standard — rule 2 especially, this piece is dense with hazard ratios
- [ ] `[F]` Publish and send
- [ ] Replace the hand-edited "Latest" block with a generated issue index
- [ ] Rework the homepage for two audiences: a prospect deciding whether to subscribe, and a subscriber returning to see what moved
- [ ] Add an RSS feed. An evidence publication that cannot be followed by machine is leaving its most patient readers out

### Phase 3 — The changelog, as a working product

The four things that must all be true. In order, because each depends on the one above.

- [ ] **Register published issues as watched entities.** Each issue gets its own source list — the trial registry entry, the company newsroom, the journal, the guideline body. This is the missing table, and it is the piece of work that makes everything below possible
- [ ] **Watch for new documents, not just corpus shifts.** `detect_changes.py` compares snapshots of claims already held. Catching "INTerpath-001 reported its numbers" needs discovery running against an issue's own sources first. Wire `00_discover_sources.py` to the issue source lists
- [ ] **Give changes their text.** `change_description` is `None` on both rows that exist. A changelog entry is prose — which question changed, what moved it, which figures differ now, whether the conclusion survived
- [ ] **Build delivery.** Notification rows to inbox does not exist in any form. This is the whole monetisable act
- [ ] **Reconcile the two subscriber models.** Signal reads Supabase users; What Holds Up is a Resend audience. Pick one as the system of record for What Holds Up and make the other follow
- [ ] **Schedule it.** Weekly, in CI, with a visible failure. Seven of nine topics still have a single snapshot and can detect nothing until they have a second
- [ ] **Build `/changelog`** in whichever shape Part 1 decides
- [ ] Backfill: there is no history. The changelog starts empty and earns entries from its first scheduled run onward. Say so on the page rather than let it look broken

### Phase 4 — Operational, before marketing to anyone

- [ ] `factcheck_recall.py` in CI, so a prompt edit that blinds a check fails visibly
- [ ] `update_masthead.py --check` in CI
- [ ] **An admin view.** One place showing every issue's state, subscriber counts and
      growth, unsubscribes, when the changelog last ran and what it found, and any drift
      between the repo and the live site. `publish.py status` answers the first part from
      a terminal; this is the rest of it. Build it as `publish.py dashboard`, writing an
      HTML file locally that is never deployed — it carries subscriber data, and a page
      at `/admin` on a static host protects nothing. A real login only becomes worth
      building when more than one person needs to see it
- [ ] A publication runbook: the exact sequence to take an issue from draft to sent, written down, so it does not live in a chat log
- [ ] Confirm `hello@`, `corrections@` and `unsubscribe@whatholdsup.org` all deliver to a mailbox someone reads
- [ ] Privacy-respecting analytics, or a decision on the record to have none
- [ ] Mobile and accessibility pass on every page
- [ ] A 404 page that offers the issue index

---

## Part 3 — Definition of done

Launch means all of the following are true at once, and none is a judgment call:

1. Two issues published, both gated, both live, both matching the repo.
2. A stranger can subscribe from the site, receives a welcome email, and can
   unsubscribe in one click — with the result recorded in our own table, not
   only in Resend's.
3. The changelog has run on a schedule at least twice without a human, has
   produced at least one real entry, and that entry reached a subscriber's
   inbox.
4. Every page on the site has been through the gate.
5. The runbook exists and someone other than its author could follow it.

Item 3 is the one that cannot be faked and the one everything else is in
service of. A site that looks finished but has never delivered a changelog
entry to a real inbox is not launched; it is a brochure.
