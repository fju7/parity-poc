# Parity Signal — Four-Tier Subscription Implementation Spec
**Priority:** High — implement immediately after claim summaries backfill
**Last updated:** March 4, 2026

---

## Overview

Replace the current three-tier subscription model (Free / Standard $4.99 / Premium $19.99) with a four-tier model that adds usage-based limits on Q&A questions and topic requests, plus a new Professional tier at $99/month.

---

## Tier Definitions

| | Free ($0) | Standard ($4.99/mo · $39.99/yr) | Premium ($19.99/mo · $149.99/yr) | Professional ($99/mo · $950/yr) |
|---|---|---|---|---|
| Subscribe to existing topics | 3 | 10 | Unlimited | Unlimited |
| Q&A questions per month | 5 | 30 | 30 | 200 |
| Included new topic requests per month | 0 | 1 | 3 | 10 |
| Additional topic requests | $9.99 each | $7.99 each | $4.99 each | $2.99 each |

---

## Stripe Products & Prices to Create

### Existing (keep as-is):
- Standard Monthly: $4.99 (price ID already in env vars)
- Standard Annual: $39.99 (price ID already in env vars)
- Premium Monthly: $19.99 (price ID already in env vars)
- Premium Annual: $149.99 (price ID already in env vars)

### New — create in Stripe Dashboard (test mode):
- **Professional Monthly:** $99.00/month (recurring)
- **Professional Annual:** $950.00/year (recurring)
- **Topic Request — Standard:** $9.99 one-time
- **Topic Request — Premium:** $4.99 one-time
- **Topic Request — Professional:** $2.99 one-time
- **Topic Request — Free:** $9.99 one-time

After creating in Stripe, add these environment variables to Render:
- `STRIPE_PRICE_PROFESSIONAL_MONTHLY`
- `STRIPE_PRICE_PROFESSIONAL_ANNUAL`
- `STRIPE_PRICE_TOPIC_REQUEST_FREE`
- `STRIPE_PRICE_TOPIC_REQUEST_STANDARD`
- `STRIPE_PRICE_TOPIC_REQUEST_PREMIUM`
- `STRIPE_PRICE_TOPIC_REQUEST_PROFESSIONAL`

---

## Database Changes

### Migration: 010_four_tier_subscriptions.sql

```sql
-- Add usage tracking columns to signal_subscriptions
ALTER TABLE signal_subscriptions 
  ADD COLUMN IF NOT EXISTS qa_questions_used INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS qa_reset_at TIMESTAMPTZ DEFAULT NOW(),
  ADD COLUMN IF NOT EXISTS topic_requests_used INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS topic_requests_reset_at TIMESTAMPTZ DEFAULT NOW();

-- Topic requests table (tracks individual requests and their status)
CREATE TABLE IF NOT EXISTS signal_topic_requests (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  raw_request TEXT NOT NULL,
  parsed_title TEXT,
  parsed_description TEXT,
  parsed_slug TEXT,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'clarification_needed', 'approved', 'processing', 'completed', 'rejected')),
  clarification_message TEXT,
  rejection_reason TEXT,
  issue_id UUID REFERENCES signal_issues(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

-- Enable RLS on topic_requests (may already exist from earlier migration)
ALTER TABLE signal_topic_requests ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist, then recreate
DROP POLICY IF EXISTS "Users can read own topic requests" ON signal_topic_requests;
DROP POLICY IF EXISTS "Users can insert own topic requests" ON signal_topic_requests;
DROP POLICY IF EXISTS "Service role full access on topic requests" ON signal_topic_requests;

CREATE POLICY "Users can read own topic requests"
  ON signal_topic_requests FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own topic requests"
  ON signal_topic_requests FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service role full access on topic requests"
  ON signal_topic_requests FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);
```

---

## Backend Changes

### 1. Update tier definitions — backend/routers/signal_stripe.py

Replace the current tier logic with:

```python
TIER_LIMITS = {
    "free":         {"topics": 3,    "qa_per_month": 5,   "topic_requests_per_month": 0},
    "standard":     {"topics": 10,   "qa_per_month": 30,  "topic_requests_per_month": 1},
    "premium":      {"topics": None, "qa_per_month": 30,  "topic_requests_per_month": 3},  # None = unlimited
    "professional": {"topics": None, "qa_per_month": 200, "topic_requests_per_month": 10},
}
```

### 2. Update GET /api/signal/tier response

Current response: `{"tier": "free"}` (or standard/premium)

New response should include usage data:
```json
{
  "tier": "professional",
  "limits": {
    "topics": null,
    "qa_per_month": 200,
    "topic_requests_per_month": 10
  },
  "usage": {
    "topics_subscribed": 7,
    "qa_questions_used": 12,
    "qa_reset_at": "2026-04-01T00:00:00Z",
    "topic_requests_used": 2,
    "topic_requests_reset_at": "2026-04-01T00:00:00Z"
  }
}
```

Usage counters reset monthly. On each /tier call, check if current date > reset_at. If so, reset counters and set reset_at to first of next month.

### 3. Update POST /api/signal/qa — add question counter

Before processing Q&A:
1. Fetch user's subscription record
2. Check `qa_questions_used < TIER_LIMITS[tier]["qa_per_month"]`
3. If at limit, return 403 with `{"error": "qa_limit_reached", "limit": 30, "used": 30, "upgrade_to": "professional"}`
4. If allowed, increment `qa_questions_used` and process the question

### 4. New endpoint: POST /api/signal/topic-request

```python
@router.post("/api/signal/topic-request")
async def request_topic(request):
    """
    Body: {"request_text": "I want to understand the evidence on intermittent fasting and longevity"}
    
    Flow:
    1. Verify user is authenticated
    2. Check tier limits for topic requests this month
    3. If at limit, return 403 with upgrade message
    4. Send request_text to Claude for parsing/validation:
       - Is this a well-formed topic that can be evaluated with evidence scoring?
       - Is it healthcare-related? (current scope limitation)
       - Suggest improved framing if unclear
       - Return: parsed_title, parsed_description, parsed_slug, is_valid, suggestion (if not valid)
    5. If valid: save to signal_topic_requests with status='approved', increment topic_requests_used
    6. If needs clarification: save with status='clarification_needed', return suggestion to user
    7. If out of scope: save with status='rejected', return explanation
    
    Response (approved):
    {"status": "approved", "title": "Intermittent Fasting and Longevity", "message": "Your topic has been queued for research. We'll notify you when it's ready."}
    
    Response (needs clarification):
    {"status": "clarification_needed", "suggestion": "Your request is broad. Consider narrowing to: 'Does intermittent fasting (16:8 or 5:2) extend lifespan or reduce age-related disease risk?' This would allow us to score specific clinical evidence.", "original": "..."}
    
    Response (rejected):
    {"status": "rejected", "reason": "This topic falls outside our current healthcare focus. We plan to expand to policy and economics topics in a future phase."}
    """
```

### 5. New endpoint: POST /api/signal/topic-request/confirm

```python
@router.post("/api/signal/topic-request/confirm")
async def confirm_topic_request(request):
    """
    After user sees the parsed/suggested topic and confirms:
    Body: {"request_id": "uuid", "confirmed_title": "...", "confirmed_description": "..."}
    
    1. Update signal_topic_requests status to 'approved'
    2. Increment topic_requests_used
    3. Return confirmation
    
    Note: The actual pipeline execution (source discovery, claim extraction, scoring)
    is Phase 1 Task 1.3 (automated pipeline). For now, approved requests are queued
    and Fred runs the pipeline manually. The notification on completion is already built.
    """
```

### 6. Update Stripe webhook handler

Add handling for Professional tier product IDs. Same pattern as Standard/Premium — map Stripe product ID to tier name, upsert signal_subscriptions.

### 7. New endpoint: POST /api/signal/topic-request/purchase

```python
@router.post("/api/signal/topic-request/purchase")
async def purchase_topic_request(request):
    """
    For users who've hit their included limit and want to buy additional requests.
    Creates a Stripe Checkout session for the one-time topic request price
    based on user's tier.
    
    On successful payment (via webhook), increment their topic request allowance by 1.
    """
```

---

## Frontend Changes

### 1. Update PricingView.jsx — Four-tier cards

Replace current three-card layout with four cards:

**Free:**
- 3 existing topics
- 5 Q&A questions/month  
- No new topic requests
- CTA: "Get Started"

**Standard — $4.99/mo or $39.99/yr:**
- 10 existing topics
- 30 Q&A questions/month
- 1 new topic request/month
- Additional requests: $9.99 each
- CTA: "Subscribe"

**Premium — $19.99/mo or $149.99/yr:**
- Unlimited existing topics
- 30 Q&A questions/month
- 3 new topic requests/month
- Additional requests: $4.99 each
- CTA: "Subscribe"
- Badge: "Most Popular"

**Professional — $99/mo or $950/yr:**
- Unlimited existing topics
- 200 Q&A questions/month
- 10 new topic requests/month
- Additional requests: $2.99 each
- CTA: "Subscribe"
- Badge: "For Organizations"

Keep the monthly/annual toggle. Show annual savings.

### 2. Update TierGate.jsx — New limits

Current: `{free: 1, standard: 5, premium: Infinity}`

New:
```javascript
const TOPIC_LIMITS = {
  free: 3,
  standard: 10,
  premium: Infinity,
  professional: Infinity
};
```

When user hits topic limit, show message:
"You're subscribed to [N] of [limit] topics on your [tier] plan. Unsubscribe from a topic or upgrade to [next tier] for more."

### 3. Update Q&A component — Question counter

Show remaining questions: "5 of 30 questions used this month"

When limit reached, show:
"You've used all [limit] questions this month. Your questions reset on [date]. Upgrade to [next tier] for more questions."

### 4. New component: TopicRequestForm.jsx

Button on Signal landing page: "Request a New Topic"

Flow:
1. Text input: "What topic would you like us to research?"
2. Submit → POST /api/signal/topic-request
3. If approved: "Great! '[Title]' has been queued. We'll notify you when research is complete."
4. If clarification needed: Show suggestion, let user accept revised framing or edit
5. If rejected: Show reason, suggest alternatives
6. If at tier limit: Show upgrade prompt or option to purchase additional request

### 5. New component: TopicRequestStatus.jsx

In user's dashboard/account area, show list of their topic requests with statuses:
- Pending → "Queued for research"
- Processing → "Research in progress"  
- Completed → "Ready! [View Topic →]"
- Clarification needed → "We have a suggestion — [Review →]"

### 6. Usage dashboard (in account/settings area)

Show current month's usage:
- Topics subscribed: 7 of 10
- Q&A questions: 12 of 30 (resets Apr 1)
- Topic requests: 1 of 3 (resets Apr 1)
- [Upgrade Plan] button

---

## Admin Notification & Approval Flow

When a topic request passes Claude's parsing/validation and the user confirms, the system should:

### 1. Notify Fred via email (Resend)

Send to fred@civicscale.ai with:
- Subject: "New Topic Request: [Parsed Title]"
- Body includes:
  - Requester's tier (Standard/Premium/Professional)
  - Original request text
  - Claude's parsed title, description, and suggested slug
  - One-click action links:
    - **Approve & Start Research** → hits admin endpoint that sets status to 'processing' (Fred then runs pipeline manually or triggers it)
    - **Request Clarification** → opens a form/page where Fred can type a message back to the requester
    - **Reject** → opens a form/page where Fred can provide a reason
  - Link to admin dashboard showing all pending requests

### 2. Admin endpoints (secured with admin check or CRON_SECRET)

```
GET  /api/signal/admin/topic-requests        — List all requests (filterable by status)
POST /api/signal/admin/topic-requests/approve — {request_id} → sets status='processing', notifies requester
POST /api/signal/admin/topic-requests/reject  — {request_id, reason} → sets status='rejected', notifies requester  
POST /api/signal/admin/topic-requests/clarify — {request_id, message} → sets status='clarification_needed', notifies requester
POST /api/signal/admin/topic-requests/complete — {request_id, issue_id} → sets status='completed', links to new issue, notifies requester, auto-subscribes them
```

### 3. Requester notifications

When Fred takes action, the requester receives:
- **Approved:** "Your topic '[Title]' has been approved and research is underway. We'll notify you when it's ready."
- **Clarification:** "We'd like to refine your topic request. [Fred's message]. Please update your request."
- **Rejected:** "We're unable to research '[Title]' at this time. [Fred's reason]."
- **Completed:** "Your topic '[Title]' is ready! [View Dashboard →]" — and they're automatically subscribed to it.

All notifications sent via email (Resend) and stored in signal_notifications for in-app display.

### 4. Admin dashboard (simple)

A lightweight page at `/signal/admin/requests` (protected — only accessible to Fred's user ID) showing:
- Pending requests with approve/clarify/reject buttons
- Processing requests (approved but not yet completed)
- Completed requests
- Request count by tier and month

This doesn't need to be fancy — a simple table with action buttons is fine for now.

---

## Implementation Order

1. **Stripe setup** — Create Professional product/prices and topic request prices via Stripe API (same method as Standard/Premium). Add env vars to Render.
2. **Database migration** — Run 010_four_tier_subscriptions.sql in Supabase SQL Editor
3. **Backend tier logic** — Update /tier endpoint with limits and usage, add counter reset logic
4. **Backend Q&A counter** — Add question counting to /qa endpoint
5. **Frontend PricingView** — Four cards with annual toggle
6. **Frontend TierGate** — Updated limits (3/10/unlimited/unlimited)
7. **Frontend Q&A counter** — Usage display and limit messaging
8. **Backend topic request** — /topic-request endpoint with Claude parsing/validation
9. **Backend admin endpoints** — /admin/topic-requests CRUD (approve, reject, clarify, complete)
10. **Admin email notification** — Resend email to fred@civicscale.ai on every confirmed request
11. **Requester notifications** — Email + in-app notifications on approve/reject/clarify/complete
12. **Frontend TopicRequestForm** — Request UI with clarification flow
13. **Frontend admin dashboard** — /signal/admin/requests page (protected to Fred's user ID)
14. **Frontend usage dashboard** — Monthly usage display
15. **Stripe topic request purchase** — One-time purchase flow for additional requests
16. **Integration testing** — Test all four tiers end-to-end

Steps 1–7 are the core subscription changes. Steps 8–13 are the topic request system with admin approval. Steps 14–15 are polish. Step 8 can be a simpler v1 that saves the request and emails Fred — the automated pipeline execution comes later.

---

## Notes

- All Stripe operations are in TEST MODE. Switch to live before charging real customers.
- Claude Code creates Stripe products/prices via the Stripe API (same method used for Standard/Premium).
- Topic request pipeline automation (source discovery → scoring → notification) is a separate task. For now, approved requests go through Fred's admin dashboard — he runs the pipeline manually.
- Q&A and topic request counters reset on the 1st of each month.
- The $950/year Professional annual price is deliberately under $1,000 to stay below most organization procurement thresholds.
- Admin dashboard is protected by checking user ID against Fred's auth.uid(). No separate admin auth system needed.
- Admin email notifications use Resend (same as existing notification delivery) to fred@civicscale.ai.
