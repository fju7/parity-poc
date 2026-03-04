# Parity Signal — Build Plan
**Product:** Evidence intelligence — six-dimension scoring, consensus mapping, Analytical Paths
**Route:** civicscale.ai/signal
**Status:** Live — Phase 0 complete, Phase 1 in progress
**Last updated:** March 4, 2026

---

## What Exists Today

### Routes
- `/signal` — Multi-topic landing page with dynamic topic discovery
- `/signal/:slug` — Topic dashboard (e.g., `/signal/glp1-drugs`)
- `/signal/methodology` — Scoring methodology explanation
- `/signal/pricing` — Subscription tiers
- `/signal/login` — Phone (SMS) authentication via Twilio

### Frontend Components (frontend/src/components/signal/)
- `SignalApp.jsx` — App shell, routing, auth, tier state
- `SignalHeader.jsx` / `SignalFooter.jsx` — Chrome
- `SignalLanding.jsx` — Multi-topic landing page (fetches from /api/signal/topics)
- `IssueDashboard.jsx` — Main topic view: summary, stats, Key Debates, categories, consensus, Q&A, claims
- `CategoryTabs.jsx` — Dynamic category navigation
- `ConsensusIndicator.jsx` — Visual consensus status display
- `ClaimCard.jsx` / `ClaimDetail.jsx` — Individual claim display with scores
- `ScoreBadge.jsx` / `EvidenceBadge.jsx` — Score visualization
- `SourceCard.jsx` — Source attribution display
- `MethodologyView.jsx` — Scoring methodology page
- `PricingView.jsx` — Three-tier pricing with monthly/annual toggle
- `TierGate.jsx` — Tier enforcement (free=1, standard=5, premium=unlimited)
- `GlossaryText.jsx` — Inline tooltip definitions for technical terms

### Backend Endpoints (backend/routers/)
- `GET /api/signal/topics` — All topics with claim counts, source counts, categories, summaries (5-min cache)
- `GET /api/signal/metrics` — Live platform stats (claims, sources, topics)
- `POST /api/signal/events` — Event capture (6 event types, anonymous UUID)
- `POST /api/signal/checkout` — Stripe checkout session creation
- `POST /api/signal/portal` — Stripe customer portal URL
- `GET /api/signal/tier` — Current user subscription tier
- `POST /api/signal/webhooks` — Stripe webhook handler
- `POST /api/signal/qa` — Premium AI Q&A (from scored evidence, not training data)
- `GET /api/signal/notifications/deliver` — Email notification delivery (via Resend, cron-triggerable)

### Backend Scripts (scripts/signal/)
- `01_ingest_sources.py` — Ingest source documents into signal_sources
- `02_extract_claims.py` — Extract claims from sources via Claude
- `03_score_claims.py` — Score claims across 6 dimensions via Claude
- `04_compute_composites.py` — Calculate composite scores from dimension scores
- `05_map_consensus.py` — Map consensus status per category
- `06_generate_summary.py` — Generate plain-language summary + glossary (v3 with accessibility)
- `07_orchestrator.py` — Full pipeline orchestrator with dry-run capability

### Database Tables (Supabase — 17 signal_ tables)
- `signal_issues` — Topics (slug, title, description, status)
- `signal_sources` — Ingested sources per issue
- `signal_claims` — Extracted claims per source
- `signal_dimension_scores` — Per-claim, per-dimension scores (6 dimensions × N claims)
- `signal_composite_scores` — Aggregated claim scores
- `signal_consensus` — Category-level consensus (consensus/debated/uncertain)
- `signal_summaries` — Versioned summaries with glossary (currently v3)
- `signal_subscriptions` — User subscription records (tier, stripe IDs)
- `signal_notifications` — Change notifications (delivered_at tracking)
- `signal_events` — Analytics events
- Plus metadata/config tables

### Live Topics
| Topic | Slug | Sources | Claims | Glossary Terms |
|-------|------|---------|--------|----------------|
| GLP-1 Weight Loss Drugs | `glp1-drugs` | 42 | ~150 | 56 |
| Breast Cancer Therapies | `breast-cancer-therapies` | 42 | ~207 | 64 |
| Social Media & Teen Mental Health | `social-media-teen-mental-health` | 41 | ~211 | 44 |
| **Total** | | **124** | **559** | **164** |

### Integrations
- Anthropic Claude API (claim extraction, scoring, summary generation, Q&A)
- Stripe (subscription billing — 3 tiers with monthly/annual)
- Twilio (SMS authentication — toll-free (888) 676-2695)
- Resend (notification email delivery — notifications@civicscale.ai)
- Supabase (auth, database, RLS)

### Subscription Tiers
| Tier | Monthly | Annual | Topics | Q&A |
|------|---------|--------|--------|-----|
| Free | $0 | $0 | 1 | No |
| Standard | $4.99 | $39.99 | 5 | No |
| Premium | $19.99 | $149.99 | Unlimited | Yes |

---

## Known Issues — Fix Before New Features

### P0: Supabase security (check RLS on signal_ tables)
- 8 signal_ tables have anonymous SELECT enabled for landing page
- This is intentional for public topic browsing
- Verify: no tables allow anonymous INSERT/UPDATE/DELETE
- Check: signal_subscriptions must NOT have anonymous SELECT

### P1: Twilio SMS verification status
- Toll-free number (888) 676-2695 configured
- Verification was "in progress" (1–3 business days) — confirm it's now verified
- If not verified, SMS auth may be unreliable

### P2: Render cold start
- Free tier spins down after inactivity
- fetchWithRetry() in SignalLanding.jsx handles this (2 retries, 1.5s delay)
- Consider: upgrade Render to paid tier if cold starts cause user drop-off

---

## Phase 1 Remaining — In Dependency Order

**Note:** Four-tier subscriptions (with topic request system, admin approval, Q&A counters) are specified separately in `spec_four_tier_subscriptions.md` and are being implemented now.

### Task 1.1: Topic Expansion to 10+ Topics
**Priority:** High — Phase 1 validation gate requires 10+ topics
**This is a pipeline execution task, not a code task:**

For each new topic:
1. Create source JSON file in `data/signal/sources/{slug}_sources.json`
2. Run: `python scripts/signal/07_orchestrator.py --issue-slug {slug}`
3. Verify: topic appears on landing page, dashboard loads, glossary tooltips work

**Suggested next topics (Fred to prioritize):**
- AI regulation / governance
- Vaccine safety & efficacy (COVID, RSV, etc.)
- Microplastics & human health
- Student loan policy
- Cannabis legalization & health effects
- Climate change economic impacts
- PFAS / forever chemicals
- Telehealth effectiveness

**Per-topic effort:** ~30 minutes (source curation) + ~60 seconds (pipeline execution)

**Verify:** Landing page shows 10+ topic cards, each with working dashboard

### Task 1.2: Analytical Paths Weight Adjustment UI
**Priority:** High — core differentiator, demonstrates the key insight
**Files to create/modify:**
- `frontend/src/components/signal/WeightAdjuster.jsx` — UI component: 6 sliders (one per dimension), real-time re-ranking of claims as weights change
- `frontend/src/components/signal/IssueDashboard.jsx` — Integrate WeightAdjuster, pass current weights to claim display
- `backend/routers/signal_weights.py` — (Optional) Endpoint to compute re-weighted composites server-side, OR do it client-side from existing dimension scores

**Design decisions:**
- Client-side recalculation preferred (all dimension scores already fetched, avoids API latency)
- Default weights: equal (1.0 each)
- Preset profiles: "Prioritize rigor" (rigor 2.0, others 1.0), "Prioritize recency" (recency 2.0, others 1.0), "Balanced" (all 1.0)
- Show: "You're seeing claims ranked by [current weight profile]. Adjust to explore how different priorities change the picture."

**Acceptance criteria:**
- 6 labeled sliders on dashboard (collapsible panel)
- Moving a slider immediately re-sorts claims by recalculated composite
- Preset buttons for common profiles
- Explanatory text: "Different analytical choices produce different rankings. This is what Analytical Paths makes visible."

**Verify:** Open GLP-1 dashboard, set "Prioritize recency" preset, confirm newest-source claims move to top. Set "Prioritize rigor" preset, confirm RCT-based claims move to top.

### Task 1.3: Web Search-Powered Evidence Ingestion
**Priority:** Medium — automates source discovery, reduces manual curation
**Files to create/modify:**
- `scripts/signal/00_discover_sources.py` — New script: takes topic description, uses web search to find relevant sources (PubMed, FDA, NIH, news outlets, advocacy groups)
- Output: draft source JSON matching existing format
- Human review required before ingestion (never auto-ingest)

**Acceptance criteria:**
- Script takes topic slug + description
- Outputs candidate source list with URL, title, source type, relevance score
- Fred reviews and approves before running pipeline

**Verify:** Run for an existing topic (GLP-1), confirm it finds sources we already have plus some we don't

---

### Task 1.4: Periodic Topic Monitoring & Update Notifications
**Priority:** High — core retention driver and key reason to stay subscribed
**Depends on:** Task 1.3 (web search source discovery) must be built first
**Sequence:** After four-tier subscriptions, after source discovery script

**Four pieces to build:**

**A. Scheduled re-check (weekly or biweekly per topic):**
- Cron job (Render cron or GitHub Action) runs source discovery for each active topic
- If new sources found → ingest, extract claims, score, recompute composites and consensus
- Compare new consensus to previous version — detect what shifted
- Store change records in signal_evidence_updates

**B. Change summary generation:**
- When scores change, Claude generates a narrative explaining what changed and why
- Example: "Two new clinical trials published since your last update shifted the consensus on cardiovascular benefits from 'debated' to 'moderate consensus.' The biggest mover: a 12,000-patient NEJM study showing 20% reduction in MACE events."
- Store in signal_evidence_updates alongside the change record

**C. Dashboard "Topic Updated" banner:**
- At top of IssueDashboard.jsx: "Updated [date] — [N] new sources added, [N] score changes. [View what changed]"
- Expands to show change summary narrative
- Only shows if topic updated since user's last visit (track via signal_events or localStorage)

**D. Subscriber email notification:**
- When a topic updates, generate notifications in signal_notifications for all subscribed users
- Email via Resend: "[Topic] updated — [one-sentence change summary]. [View Dashboard →]"
- Respects notification preferences (signal_notification_preferences)
- Uses existing signal_notify_deliver.py endpoint

**Verify:** Manually add a new source to an existing topic, run pipeline, confirm: evidence_updates record created, dashboard banner appears, notification generated, email sent to subscribed users.

---

## Phase 2 — Documented, Not Yet

- Community features (user comments on claims, upvote/downvote on usefulness)
- Embeddable widgets (media organizations embed Signal scores in articles)
- API access tier (researchers and organizations query scored data programmatically)
- Signal beyond healthcare (government policy, science, economics)

---

## Pipeline Architecture Reference

```
Sources JSON → 01_ingest → 02_extract → 03_score → 04_composite → 05_consensus → 06_summary
                  ↓            ↓           ↓            ↓              ↓              ↓
            signal_sources → signal_claims → signal_dimension_scores → signal_composite_scores → signal_consensus → signal_summaries
```

Full pipeline: `python scripts/signal/07_orchestrator.py --issue-slug {slug}`
Dry run: `python scripts/signal/07_orchestrator.py --issue-slug {slug} --dry-run`
Single step: `python scripts/signal/03_score_claims.py --issue-slug {slug}`
