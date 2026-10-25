# CivicScale's SMS sign-in sender is shared with Grailr (2026-10-25)

Recorded from the Grailr launch-readiness work (Grailr launch checklist P18 / P19; Grailr triage §54–§55), because
the finding is about CivicScale's sign-in as much as Grailr's. Read in the Twilio console on 2026-10-25; nothing was
changed there.

## What is shared

- The Twilio account has **one** Messaging Service, **"CivicScale Auth"** (`MGa19bc5c6632208aec5feddc10f09fad6`,
  use case "Verify users"), with **one** sender: toll-free **+1 888 676 2695**.
- Grailr's Supabase Auth also sends its phone sign-in codes through this Messaging Service
  (`sms_provider = twilio`; Grailr's template is "Your code is …").
- The number's **Toll-Free Verification** (HH237f1f2c63eb0c842891129d77534029, Approved, Mar 17 2026) describes
  CivicScale only: Account Notifications, ~100 SMS/month, "CivicScale uses SMS solely for one-time login verification
  codes. Users navigate to civicscale.ai/signal…", sample "Your Parity Signal verification code is: 123456",
  terms/privacy/opt-in proof on civicscale.ai.

## Why it matters to CivicScale

1. **One opt-out list.** The service's opt-out keywords include STOP ("no further messages from this number"). A
   person who replies STOP to a Grailr code can no longer receive CivicScale codes from this number, and vice versa,
   until they text START.
2. **Grailr's abuse lands on CivicScale's sender.** Four SMS-pumping bursts (2026-09-01, 09-29, 10-08; plus a
   setup-shaped one on 03-03) came through Grailr's Supabase project. Geo permissions (US/Canada only) blocked every
   international send; a non-geographic +1 500 number was delivered. Those bursts spend this sender's reputation and
   the shared balance, and they spend Supabase's SMS rate limit for Grailr (not CivicScale's — separate Supabase
   projects).
3. **Traffic outside the verification.** Grailr's codes are not the use case this number was verified for. Carriers
   can suspend a toll-free number whose traffic does not match its verification — that would stop CivicScale's
   phone sign-in too.
   *As of 2026-10-25, both products are pre-launch with no outside users,* so a suspension today would affect two
   development products and no users. The point above describes how suspension works; it makes no claim about users.
4. **One balance.** Auto-recharge is on ($10 → $50, one card, no backup method); the low-balance email ($5) goes to
   account owners. Both products draw on it.

## Proposed (in Grailr's records, awaiting a decision)

Move Grailr off this sender: either **Twilio Verify** for Grailr (`twilio_verify` in Grailr's Supabase; $0.0583 per
successful US verification; managed sender pool; Fraud Guard included) — recommended — or a second Messaging Service
and toll-free number for Grailr with its own Toll-Free Verification ($2.15/month; approval takes days to weeks).
Either leaves this number, its verification and its opt-out list to CivicScale alone. Neither separates the balance;
that would need separate billing.

Nothing in CivicScale's code or configuration was changed by this note.
