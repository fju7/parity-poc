# Parity Signal — Claude Code Handoff Document

## Read This First

This document contains everything you need to know to begin building the Parity Signal prototype. It was created through extensive strategic and technical design sessions. **Do not deviate from the architecture, schema, or design decisions described here without explicit approval from the user.**

Before writing any code: examine the actual repository structure, verify existing file paths, database configuration, and tech stack. Do not assume filenames or directory structures.

---

## What Is Parity Signal?

Parity Signal is Product 4 under CivicScale (civicscale.ai). It extends the Parity Engine — which currently powers three healthcare billing products — from benchmark-based billing analysis to AI-powered claim intelligence for complex public issues.

**What we are building:** An AI-powered system that ingests public sources about a topic, extracts discrete factual claims, scores each claim against available evidence across multiple transparent dimensions, maps consensus and disagreement, and produces structured summaries that help consumers understand what the evidence actually says.

**What we are NOT building:** A fact-checker, a news aggregator, or a media outlet. We do not declare things true or false. We score claims against evidence with transparent methodology and let users draw their own conclusions.

**First topic:** GLP-1 drugs (semaglutide/Ozempic/Wegovy, tirzepatide/Mounjaro/Zepbound).

---

## Existing Infrastructure

Parity Signal lives within the existing CivicScale monorepo:

- **Frontend:** React + Vite, deployed on Vercel
- **Backend:** FastAPI (Python), deployed on Render
- **Database:** Supabase (PostgreSQL)
- **Authentication:** Magic link auth via Supabase + Resend (existing); SMS code auth via Supabase Phone Auth + Twilio (new for Signal)
- **AI:** Anthropic Claude API
- **Payments:** Stripe (account established, ready for integration)
- **Repository:** GitHub — fju7/parity-poc

---

## Starting Point: Infrastructure First

We are starting with the data infrastructure: Supabase schema, authentication, and the scoring pipeline. The rationale is that when we build the UI, it will have real data to display rather than mocks.

### Immediate Tasks (in order):

**1. Database Schema Creation**

Create all Parity Signal tables in Supabase. The complete schema is below. Key design decisions already made:

- Per-dimension scores stored separately (not just composites) — this is critical for the Analytical Paths feature coming in Phase 1
- Dimension weights stored as configurable JSONB, not hardcoded
- Event capture table included from the start — every interaction must be logged from day one
- Subscription/tier tables included but Stripe integration comes later

```sql
-- Core content tables

CREATE TABLE signal_issues (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE signal_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id UUID REFERENCES signal_issues(id),
  title TEXT NOT NULL,
  url TEXT,
  source_type TEXT NOT NULL,           -- clinical_trial, fda, cms, pricing, public_reporting
  publication_date DATE,
  retrieved_at TIMESTAMPTZ DEFAULT now(),
  content_text TEXT,                    -- full text or structured summary
  metadata JSONB                        -- flexible additional metadata
);

CREATE TABLE signal_claims (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id UUID REFERENCES signal_issues(id),
  claim_text TEXT NOT NULL,
  category TEXT NOT NULL,               -- efficacy, safety, cardiovascular, pricing, regulatory, emerging
  specificity TEXT,                      -- quantitative, qualitative, mixed
  extracted_at TIMESTAMPTZ DEFAULT now(),
  extraction_model TEXT
);

CREATE TABLE signal_claim_sources (
  claim_id UUID REFERENCES signal_claims(id),
  source_id UUID REFERENCES signal_sources(id),
  source_context TEXT,                  -- specific passage
  PRIMARY KEY (claim_id, source_id)
);

CREATE TABLE signal_claim_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id UUID REFERENCES signal_claims(id),
  dimension TEXT NOT NULL,              -- source_quality, data_support, reproducibility, consensus, recency, rigor
  score INTEGER CHECK (score BETWEEN 1 AND 5),
  rationale TEXT,
  scored_at TIMESTAMPTZ DEFAULT now(),
  scoring_model TEXT
);

CREATE TABLE signal_claim_composites (
  claim_id UUID PRIMARY KEY REFERENCES signal_claims(id),
  composite_score NUMERIC(3,2),
  evidence_category TEXT,               -- strong, moderate, mixed, weak
  weights_used JSONB,
  scored_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE signal_consensus (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id UUID REFERENCES signal_issues(id),
  category TEXT NOT NULL,
  consensus_status TEXT NOT NULL,        -- consensus, debated, uncertain
  summary_text TEXT,
  supporting_claim_ids JSONB,
  arguments_for TEXT,                    -- for debated claims
  arguments_against TEXT,                -- for debated claims
  mapped_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE signal_summaries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id UUID REFERENCES signal_issues(id),
  version INTEGER DEFAULT 1,
  summary_json JSONB,
  summary_text TEXT,
  generated_at TIMESTAMPTZ DEFAULT now(),
  generation_model TEXT
);

-- Subscription and tier management

CREATE TABLE signal_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  tier TEXT NOT NULL DEFAULT 'free',        -- free, standard, premium
  billing_period TEXT,                       -- monthly, annual (null for free)
  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  status TEXT NOT NULL DEFAULT 'active',     -- active, canceled, past_due, trialing
  current_period_start TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE signal_topic_subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  issue_id UUID REFERENCES signal_issues(id),
  subscribed_at TIMESTAMPTZ DEFAULT now(),
  unsubscribed_at TIMESTAMPTZ,              -- null if currently active
  status TEXT NOT NULL DEFAULT 'active',     -- active, swapped, canceled
  UNIQUE(user_id, issue_id)
);

-- Evidence updates and notifications

CREATE TABLE signal_evidence_updates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  issue_id UUID REFERENCES signal_issues(id),
  claim_id UUID REFERENCES signal_claims(id),
  change_type TEXT NOT NULL,                -- score_shift, consensus_change, new_claim, new_source
  previous_score NUMERIC(3,2),
  new_score NUMERIC(3,2),
  previous_category TEXT,
  new_category TEXT,
  change_description TEXT,
  source_id UUID REFERENCES signal_sources(id),
  detected_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE signal_notification_preferences (
  user_id UUID PRIMARY KEY REFERENCES auth.users(id),
  method TEXT NOT NULL DEFAULT 'push',      -- push, sms, email
  frequency TEXT NOT NULL DEFAULT 'immediate',
  major_shifts_only BOOLEAN DEFAULT false,
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE signal_notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  update_id UUID REFERENCES signal_evidence_updates(id),
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  deep_link TEXT,
  delivery_method TEXT NOT NULL,
  delivered_at TIMESTAMPTZ,
  read_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Topic requests (Premium feature)

CREATE TABLE signal_topic_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id),
  topic_name TEXT NOT NULL,
  description TEXT,
  reference_urls JSONB,
  status TEXT NOT NULL DEFAULT 'submitted',
  published_issue_id UUID REFERENCES signal_issues(id),
  submitted_at TIMESTAMPTZ DEFAULT now(),
  resolved_at TIMESTAMPTZ
);

-- Event capture and analytics

CREATE TABLE signal_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID,
  event_type TEXT NOT NULL,
  event_data JSONB,
  device_type TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_signal_events_type_date ON signal_events(event_type, created_at);
CREATE INDEX idx_signal_events_user ON signal_events(user_id, created_at);

-- Platform metrics cache

CREATE TABLE signal_platform_metrics (
  metric_key TEXT PRIMARY KEY,
  metric_value NUMERIC,
  display_label TEXT,
  display_order INTEGER,
  visible BOOLEAN DEFAULT false,
  refreshed_at TIMESTAMPTZ DEFAULT now()
);

-- Analytical Paths (Phase 1 — create table now for readiness)

CREATE TABLE signal_analytical_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  weights JSONB NOT NULL,
  trade_off_summary TEXT,
  source_type_association TEXT,
  is_default BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**2. Source Library Assembly**

Curate the public evidence base for GLP-1 drugs. Target: 30-50 sources.

Source categories:
- FDA: approval documents, labels, safety communications for semaglutide and tirzepatide
- Clinical trials: STEP trials, SURMOUNT trials, SELECT cardiovascular trial (ClinicalTrials.gov + published results)
- CMS/Insurance: Medicare coverage decisions, legislative changes
- Pricing: manufacturer list prices, international comparisons, biosimilar pipeline
- Public reporting: AP/Reuters, public health agency statements, congressional hearings

Create a `/data/signal/sources/` directory. Store source metadata in a JSON manifest per source. Build `scripts/signal/collect_sources.py` to fetch and organize.

**3. Claim Extraction Pipeline**

Build `scripts/signal/extract_claims.py` that sends source content to Claude API with structured prompts to extract discrete factual claims.

A "claim" is a specific, testable assertion of fact. Not a summary, not an opinion.

Claim categories: efficacy, safety, cardiovascular, pricing/access, regulatory, emerging/speculative.

Deduplicate: when multiple sources make the same claim, link them via the `signal_claim_sources` junction table rather than creating duplicate claims.

Target: 50-100 extracted claims.

**4. Evidence Scoring Engine**

Build `scripts/signal/score_claims.py` that scores each claim across six dimensions:

| Dimension | Description | Weight |
|-----------|-------------|--------|
| Source Quality | How authoritative is the primary source? | 25% |
| Data Support | Is there quantitative data directly supporting the claim? | 20% |
| Reproducibility | Has the finding been replicated independently? | 20% |
| Consensus Level | What proportion of credible sources agree? | 15% |
| Recency | How current is the evidence? | 10% |
| Methodological Rigor | Study design quality / analytical rigor | 10% |

Composite: weighted average mapped to Strong (4.0-5.0), Moderate (3.0-3.9), Mixed (2.0-2.9), Weak (1.0-1.9).

**CRITICAL:** Store per-dimension scores AND weights separately. This is required for Analytical Paths in Phase 1. Do not store only composites.

**5. Authentication: Add SMS Code Option**

Add SMS code auth alongside existing magic links:
- Supabase `signInWithOtp` with `phone` parameter
- Twilio as SMS delivery provider
- User flow: enter phone → receive 6-digit code → enter code → authenticated
- Users choose email or phone at signup; both link to same account
- Phone option is visually primary in Signal (mobile-first product)

Verify current Supabase phone auth docs before implementing.

---

## Scoring Methodology — Key Design Decisions

These are settled decisions. Do not change them:

1. **We score claims, not articles.** We extract individual assertions and score each one. We do not evaluate or rate entire articles or sources.

2. **We do not declare true/false.** We score evidence strength. "Strong evidence" means high-quality, replicated, recent, rigorous. Not "this is true."

3. **All weights are disclosed.** The default weights (25/20/20/15/10/10) are published in the methodology. Users will be able to see them. In Phase 1, they'll be able to adjust them.

4. **Transparency is non-negotiable.** Every score has a visible rationale. Every dimension score is individually viewable. The methodology page explains everything.

---

## Subscription Model

Three tiers (Stripe integration comes after core pipeline):

| Feature | Free | Standard ($4.99/mo) | Premium ($19.99/mo) |
|---------|------|---------------------|---------------------|
| Topics | 1 (swap anytime) | Up to 5 | Unlimited |
| Summaries & Scores | Full access | Full access | Full access |
| Evidence Updates | Yes | Yes | Yes |
| Q&A | — | — | Yes |
| Topic Requests | — | — | Yes |
| Annual Pricing | — | $39.99/yr | $149.99/yr |

Free tier gets updates because the conversion trigger is breadth (wanting a second topic), not depth.

---

## Mobile-First Design

Signal's usage pattern is fundamentally different from the billing products. Users check scored claims the way they check news: on their phone, during downtime.

- Touch-friendly with large tap targets
- Summary first, drill-down on demand (progressive disclosure)
- Swipeable category tabs, not sidebar navigation
- Accordion pattern for claim details (stay in context, no page loads)
- SMS auth as primary sign-in method
- `navigator.sendBeacon` for reliable event capture on mobile

The billing products remain laptop-optimized. Signal is a separate design track.

---

## Phase 1 Preview: Analytical Paths

Not built now, but the architecture must support it. This is the platform's deepest differentiator.

**Concept:** When different sources reach different conclusions about the same claim, the difference is almost always in the analytical weights — which factors they emphasize and which they de-prioritize. Analytical Paths makes those weight choices visible and explorable.

**How it works:** User taps "Why might other sources see this differently?" → sees alternative analytical profiles (e.g., "Prioritize Newest Evidence" shifts recency to 40%, rigor to 5%) → composite score recalculates in real time → AI-generated explanation of what each weighting assumes and trades off.

**Pre-built profiles:**

| Profile | Emphasis | Maps To |
|---------|----------|---------|
| Prioritize Newest Evidence | Recency 40%, Rigor 5% | News outlets |
| Prioritize Largest Studies | Rigor 35%, Reproducibility 25% | Regulatory agencies |
| Prioritize Regulatory Consensus | Source Quality 40%, Consensus 25% | Regulatory agencies |
| Prioritize Real-World Outcomes | Data Support 30%, Recency 25% | Patient advocacy |
| Prioritize Personal Experience | Recency 35%, Data Support 10% | Social media |

**Why this matters:** Requires persistent scoring infrastructure (per-dimension scores, configurable weights, stored profiles). Cannot be replicated with prompt engineering. This is the answer to "isn't this just ChatGPT?"

**Cross-platform:** Same capability applies to denial management in Parity Provider (showing the analytical path a payer followed to deny a claim) and Parity Employer (making TPA's invisible analytical choices visible to the employer paying the bills).

---

## Proposed File Structure

Adapt to actual repo layout after examination:

```
# Backend additions (within existing FastAPI structure)
api/
  signal/
    routes.py
    models.py
    service.py
    stripe_webhooks.py
    subscription_service.py
    notification_service.py

scripts/
  signal/
    collect_sources.py       # Task 1
    extract_claims.py        # Task 2
    score_claims.py          # Task 3
    map_consensus.py         # Task 4
    generate_summary.py      # Task 5
    detect_changes.py        # Task 9
    generate_notifications.py
    run_pipeline.py          # Orchestrator

data/
  signal/
    sources/
    manifests/

# Frontend additions (within existing React structure)
src/
  pages/
    signal/
      IssueSummary.jsx
      MyTopics.jsx
      Methodology.jsx
      SignalChat.jsx
      SignalLogin.jsx
      RequestTopic.jsx
  components/
    signal/
      ClaimCard.jsx
      ClaimDetail.jsx
      ScoreDisplay.jsx
      ConsensusMap.jsx
      EvidenceBadge.jsx
      CategoryTabs.jsx
      SubscribeButton.jsx
      TierGate.jsx
      UpdateBanner.jsx
      PhoneAuth.jsx
```

---

## Key Principles

1. **Transparency above all.** Every score has a visible rationale. Every weight is disclosed.
2. **Claims, not articles.** Extract and score individual assertions.
3. **No opinions.** The system shows evidence strength and consensus. It does not take sides.
4. **Evidence-grounded Q&A.** Responses are traceable to scored claims and sources.
5. **Plain language.** Output must be useful to someone with no medical or policy background.
6. **Capture everything from day one.** Event logging starts with the first user interaction.
7. **Architecture for Analytical Paths.** Per-dimension scores and configurable weights in every scoring operation.

---

## What NOT to Do

- Do not hardcode scoring weights. They must be configurable JSONB.
- Do not store only composite scores. Per-dimension scores are required.
- Do not build authentication that only supports email. SMS code must be an option.
- Do not design for desktop first. Signal is mobile-first.
- Do not express opinions in AI-generated content. Evidence strength, not truth claims.
- Do not skip event capture. It cannot be retrofitted.
- Do not assume file paths or directory structures. Verify the actual repo before creating files.
