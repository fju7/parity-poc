# Benchmark Observations — Crowdsourced Commercial Rate Database

## Overview

Every bill analyzed through Parity Health generates anonymized data points that are stored in a benchmark observations table. Over time, this becomes a crowdsourced commercial rate database that powers increasingly accurate benchmarks across all three billing products.

---

## Database Schema

### Table: `benchmark_observations`

```sql
CREATE TABLE benchmark_observations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cpt_code TEXT NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  amount_type TEXT NOT NULL CHECK (amount_type IN (
    'billed_amount', 'allowed_amount', 'patient_responsibility',
    'deductible_applied', 'plan_paid'
  )),
  insurer TEXT,                          -- normalized: 'cigna', 'aetna', 'uhc', 'bcbs', etc.
  insurer_raw TEXT,                      -- original text before normalization for auditing
  region TEXT NOT NULL,                  -- metro area or state, e.g. 'chicago_suburbs_il'
  state_code TEXT,                       -- two-letter state code, e.g. 'IL'
  zip3 TEXT,                             -- first 3 digits of ZIP only (e.g. '600') — enough for region, not enough to identify
  provider_specialty TEXT,               -- inferred from CPT codes or stated, e.g. 'dermatology'
  network_status TEXT DEFAULT 'unknown' CHECK (network_status IN (
    'in_network', 'out_of_network', 'unknown'
  )),
  facility_type TEXT DEFAULT 'unknown' CHECK (facility_type IN (
    'office', 'hospital_outpatient', 'hospital_inpatient',
    'asc', 'er', 'urgent_care', 'telehealth', 'unknown'
  )),
  service_month TEXT,                    -- 'YYYY-MM' format only, never exact date
  confidence TEXT DEFAULT 'medium' CHECK (confidence IN ('high', 'medium', 'low')),
  input_method TEXT NOT NULL CHECK (input_method IN (
    'pdf_upload', 'paste_text', 'image_upload', 'manual_entry', 'sample_bill'
  )),
  is_outlier BOOLEAN DEFAULT FALSE,     -- flagged by statistical outlier detection
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common benchmark queries
CREATE INDEX idx_bench_cpt_region ON benchmark_observations(cpt_code, region);
CREATE INDEX idx_bench_cpt_insurer ON benchmark_observations(cpt_code, insurer);
CREATE INDEX idx_bench_cpt_state ON benchmark_observations(cpt_code, state_code);
CREATE INDEX idx_bench_region_specialty ON benchmark_observations(region, provider_specialty);
CREATE INDEX idx_bench_created ON benchmark_observations(created_at);
CREATE INDEX idx_bench_confidence ON benchmark_observations(confidence) WHERE confidence != 'low';
```

### What is NOT in this table
- No user_id — observations are fully anonymous, cannot be traced back to a user
- No patient name, DOB, or any identifying information
- No provider name or exact address — only specialty and region
- No exact date of service — only month/year
- No claim ID or reference numbers
- No foreign keys to any user table

### RLS Policy
```sql
-- No one can read individual observations through the API
-- Only the backend service role can insert
-- Aggregate views (created later) will be publicly readable
ALTER TABLE benchmark_observations ENABLE ROW LEVEL SECURITY;

-- Backend service can insert
CREATE POLICY "service_insert" ON benchmark_observations
  FOR INSERT TO service_role WITH CHECK (true);

-- No direct SELECT for anonymous or authenticated users
-- All reads go through aggregate views or backend API
```

---

## Insurer Normalization

Map messy portal text to standard insurer identifiers:

```python
INSURER_ALIASES = {
    'cigna': ['cigna', 'cigna healthcare', 'cigna health', 'evernorth'],
    'aetna': ['aetna', 'aetna health', 'cvs health', 'cvs/aetna'],
    'uhc': ['united', 'unitedhealthcare', 'united healthcare', 'uhc', 'optum'],
    'bcbs': ['blue cross', 'blue shield', 'bcbs', 'anthem', 'carefirst',
             'highmark', 'premera', 'regence', 'horizon', 'independence',
             'excellus', 'wellmark', 'florida blue', 'blue cross blue shield'],
    'humana': ['humana'],
    'kaiser': ['kaiser', 'kaiser permanente'],
    'tricare': ['tricare'],
    'medicare_advantage': ['medicare advantage', 'ma plan'],
    'medicaid_managed': ['medicaid', 'managed medicaid'],
    'other': []  # fallback
}

def normalize_insurer(raw_text: str) -> tuple[str, str]:
    """Returns (normalized_key, raw_text)"""
    lower = raw_text.lower().strip()
    for key, aliases in INSURER_ALIASES.items():
        for alias in aliases:
            if alias in lower:
                return key, raw_text
    return 'other', raw_text
```

---

## Provider Specialty Inference

When the portal data doesn't explicitly state specialty, infer from CPT codes:

```python
CPT_SPECIALTY_MAP = {
    # Dermatology
    '11102': 'dermatology', '11103': 'dermatology', '11104': 'dermatology',
    '17000': 'dermatology', '17003': 'dermatology', '17004': 'dermatology',
    # Cardiology
    '93000': 'cardiology', '93010': 'cardiology', '93306': 'cardiology',
    '93307': 'cardiology', '93308': 'cardiology', '93320': 'cardiology',
    # Orthopedics
    '27447': 'orthopedics', '27130': 'orthopedics', '29881': 'orthopedics',
    # Primary Care / E&M (ambiguous — default to 'primary_care')
    '99213': 'primary_care', '99214': 'primary_care', '99215': 'primary_care',
    '99203': 'primary_care', '99204': 'primary_care', '99205': 'primary_care',
    # Imaging
    '70553': 'radiology', '73721': 'radiology', '74177': 'radiology',
    # Lab
    '80053': 'laboratory', '85025': 'laboratory', '36415': 'laboratory',
}

def infer_specialty(cpt_codes: list[str]) -> str:
    """Infer provider specialty from the most common specialty across CPT codes."""
    specialties = [CPT_SPECIALTY_MAP.get(code, 'unknown') for code in cpt_codes]
    specialties = [s for s in specialties if s != 'unknown']
    if not specialties:
        return 'unknown'
    # Return most frequent
    from collections import Counter
    return Counter(specialties).most_common(1)[0][0]
```

---

## Region Derivation

Convert ZIP codes to anonymized regions. Never store full ZIP codes — use ZIP3 (first 3 digits) plus a metro area name.

```python
# Simplified — in production, use a ZIP-to-CBSA mapping table
ZIP3_TO_REGION = {
    '600': 'chicago_suburbs_il',
    '606': 'chicago_il',
    '100': 'manhattan_ny',
    '900': 'los_angeles_ca',
    '941': 'san_francisco_ca',
    '770': 'houston_tx',
    '331': 'miami_fl',
    '200': 'washington_dc',
    # ... extend with full ZIP3-to-metro mapping
}

def derive_region(zip_code: str) -> tuple[str, str, str]:
    """Returns (region_name, state_code, zip3)"""
    zip3 = zip_code[:3]
    region = ZIP3_TO_REGION.get(zip3, f'region_{zip3}')
    # State from ZIP is approximate but good enough for benchmarking
    state = ZIP_TO_STATE.get(zip3, 'unknown')
    return region, state, zip3
```

---

## Outlier Detection

Flag statistically implausible amounts before storing:

```python
# Per-CPT expected ranges (approximate, from Medicare + commercial multiplier)
# In production, these would be derived from existing data
CPT_AMOUNT_RANGES = {
    '99213': (50, 500),
    '99214': (75, 700),
    '99215': (100, 900),
    '11102': (80, 800),
    '93306': (100, 1500),
    '27447': (1500, 50000),
    # ... extend as data grows
}

# Fallback: any amount under $1 or over $100,000 is suspicious
DEFAULT_RANGE = (1, 100000)

def check_outlier(cpt_code: str, amount: float) -> bool:
    """Returns True if the amount is likely an outlier."""
    low, high = CPT_AMOUNT_RANGES.get(cpt_code, DEFAULT_RANGE)
    return amount < low or amount > high
```

Once you have 20+ observations for a CPT code in a region, switch to statistical detection:
- Flag anything more than 3 standard deviations from the mean for that CPT + region
- Store flagged observations but exclude them from benchmark calculations

---

## Saving Observations — Backend Logic

### New function: `save_benchmark_observations()`

Called after the user confirms their bill analysis and the benchmark report is generated. This is the last step — the user has already reviewed and corrected the extracted data.

```python
async def save_benchmark_observations(
    line_items: list[dict],     # confirmed line items from analysis
    insurer: str | None,        # detected or user-entered insurer
    zip_code: str,              # from confirmation screen
    network_status: str,        # from extraction
    input_method: str,          # 'pdf_upload', 'paste_text', 'image_upload', etc.
    service_date: str | None,   # full date from bill — we only store month
    provider_specialty: str | None  # detected or inferred
):
    """
    Anonymize and store benchmark observations from a completed bill analysis.
    """
    insurer_normalized, insurer_raw = normalize_insurer(insurer) if insurer else ('unknown', None)
    region, state_code, zip3 = derive_region(zip_code)
    service_month = service_date[:7] if service_date else None  # '2026-02-16' -> '2026-02'
    
    if not provider_specialty:
        cpt_codes = [item['cpt_code'] for item in line_items if item.get('cpt_code')]
        provider_specialty = infer_specialty(cpt_codes)
    
    observations = []
    for item in line_items:
        if not item.get('cpt_code') or not item.get('amount'):
            continue  # skip items without core data
        
        amount = float(item['amount'])
        is_outlier = check_outlier(item['cpt_code'], amount)
        
        # Determine confidence from extraction confidence + outlier status
        confidence = item.get('cpt_confidence', 'medium')
        if confidence == 'inferred':
            confidence = 'low'
        if is_outlier:
            confidence = 'low'
        
        observations.append({
            'cpt_code': item['cpt_code'],
            'amount': amount,
            'amount_type': item.get('amount_type', 'billed_amount'),
            'insurer': insurer_normalized,
            'insurer_raw': insurer_raw,
            'region': region,
            'state_code': state_code,
            'zip3': zip3,
            'provider_specialty': provider_specialty,
            'network_status': network_status or 'unknown',
            'facility_type': item.get('facility_type', 'unknown'),
            'service_month': service_month,
            'confidence': confidence,
            'input_method': input_method,
            'is_outlier': is_outlier
        })
    
    # Batch insert into Supabase
    if observations:
        supabase.table('benchmark_observations').insert(observations).execute()
    
    return len(observations)
```

### Integration Point

In the existing bill analysis endpoint (or the new `analyze-confirmed` endpoint), add this call after generating the benchmark report:

```python
# After benchmark analysis is complete and results are returned to user:
observation_count = await save_benchmark_observations(
    line_items=confirmed_request.line_items,
    insurer=confirmed_request.insurer,
    zip_code=confirmed_request.zip_code,
    network_status=confirmed_request.network_status,
    input_method=confirmed_request.input_method,
    service_date=confirmed_request.service_date,
    provider_specialty=confirmed_request.provider_specialty
)
# Optional: include in response
# "Your anonymized data (X observations) has been added to our benchmark database."
```

---

## User Consent

### Consent Language (shown during analysis flow)

Add to the confirmation screen, before the "Run Analysis" button:

```
☑ Anonymize my bill data and add it to CivicScale's benchmark database
  to help make healthcare pricing more transparent.
  
  We store only: procedure codes, amounts, insurer, region, and date (month/year).
  No personal information, provider names, or identifying details are saved.
  [Learn more]
```

- Checkbox is ON by default (opt-out model — most users won't change it)
- If unchecked, skip the save_benchmark_observations call
- "Learn more" links to a brief privacy explanation on the methodology page

### Post-Analysis Message

After analysis completes, if consent was given:

```
"Your analysis is complete. Your anonymized data has been added to our 
benchmark database, helping make healthcare pricing more transparent 
for everyone. Thank you."
```

---

## Aggregate Views (for future use)

Once sufficient data accumulates, create materialized views for fast benchmark queries:

```sql
-- Aggregate benchmarks by CPT + region
CREATE MATERIALIZED VIEW benchmark_aggregates AS
SELECT 
  cpt_code,
  region,
  state_code,
  insurer,
  amount_type,
  network_status,
  COUNT(*) as observation_count,
  ROUND(AVG(amount)::numeric, 2) as avg_amount,
  ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY amount)::numeric, 2) as median_amount,
  ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY amount)::numeric, 2) as p25_amount,
  ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY amount)::numeric, 2) as p75_amount,
  ROUND(MIN(amount)::numeric, 2) as min_amount,
  ROUND(MAX(amount)::numeric, 2) as max_amount,
  ROUND(STDDEV(amount)::numeric, 2) as stddev_amount
FROM benchmark_observations
WHERE is_outlier = FALSE
  AND confidence != 'low'
GROUP BY cpt_code, region, state_code, insurer, amount_type, network_status
HAVING COUNT(*) >= 5;  -- minimum 5 observations to show a benchmark

-- Refresh nightly via cron
-- REFRESH MATERIALIZED VIEW benchmark_aggregates;
```

### Minimum Display Thresholds

To protect privacy and ensure statistical meaning:
- **5+ observations** required to show any benchmark for a CPT + region combination
- **10+ observations** required to show insurer-specific benchmarks
- **20+ observations** required to show percentile ranges (25th/75th)
- Never expose individual observations through any API

---

## Metrics & Monitoring

### Dashboard Additions

Add to the existing admin or internal metrics:

```sql
-- Total observations
SELECT COUNT(*) as total_observations FROM benchmark_observations;

-- Observations by input method
SELECT input_method, COUNT(*) FROM benchmark_observations GROUP BY input_method;

-- Observations by insurer
SELECT insurer, COUNT(*) FROM benchmark_observations GROUP BY insurer ORDER BY count DESC;

-- Top CPT codes by observation count
SELECT cpt_code, COUNT(*) FROM benchmark_observations GROUP BY cpt_code ORDER BY count DESC LIMIT 20;

-- Outlier rate
SELECT 
  COUNT(*) FILTER (WHERE is_outlier) as outliers,
  COUNT(*) as total,
  ROUND(100.0 * COUNT(*) FILTER (WHERE is_outlier) / COUNT(*), 1) as outlier_pct
FROM benchmark_observations;

-- Coverage: how many CPT+region combos have 5+ observations
SELECT COUNT(*) as benchmark_ready_combos
FROM (
  SELECT cpt_code, region
  FROM benchmark_observations
  WHERE is_outlier = FALSE AND confidence != 'low'
  GROUP BY cpt_code, region
  HAVING COUNT(*) >= 5
) sub;
```

### Public Metrics (for landing page)

Extend the existing metrics endpoint to include benchmark database stats:

```json
{
  "signal": { "claims": 559, "sources": 124, "topics": 3 },
  "benchmark": {
    "observations": 2,
    "regions": 1,
    "insurers": 1,
    "cpt_codes": 2
  }
}
```

As numbers grow, these become compelling: "12,000+ real-world pricing observations across 340 CPT codes and 28 metro areas."

---

## Implementation Priority

1. **Create the Supabase table** with the schema above
2. **Build save_benchmark_observations()** function with insurer normalization, specialty inference, region derivation, and outlier detection
3. **Add consent checkbox** to the confirmation screen
4. **Wire up the save call** after successful bill analysis
5. **Add post-analysis message** confirming data contribution
6. **Update metrics endpoint** to include benchmark observation counts

Items 1-6 are the core build. Aggregate views, materialized views, and the transition from Medicare-only to community benchmarks come later as data volume grows.

---

## Privacy Checklist

- [ ] No user_id in observations table
- [ ] No patient name, DOB, or identifiers stored
- [ ] No provider name stored (only specialty)
- [ ] No exact date (month/year only)
- [ ] No full ZIP code (ZIP3 only)
- [ ] Minimum 5 observations before displaying any benchmark
- [ ] Outliers flagged and excluded from aggregates
- [ ] Consent checkbox visible and functional
- [ ] "Learn more" link explains what is/isn't stored
- [ ] RLS prevents direct reads of individual observations
