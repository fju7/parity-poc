# Historical Rate Versioning — Operations Guide

## Overview

The rate versioning system allows Parity Health to benchmark bills against
CMS rates that were in effect at the time of service, not just the current
year's rates. This is critical for older bills where rates may have changed.

**Architecture:**
- Current-year rates (2026) remain in CSV files loaded into memory at startup (fast path)
- Historical rates are stored in Supabase tables and queried only when needed
- The `rate_schedule_versions` table is the registry of all loaded vintages

## Tables

| Table | Purpose |
|-------|---------|
| `rate_schedule_versions` | Registry of all loaded rate schedule vintages |
| `pfs_rates_historical` | Versioned PFS rates (841K+ rows per year) |
| `opps_rates_historical` | Versioned OPPS rates (~7K rows per year) |
| `clfs_rates_historical` | Versioned CLFS rates (~2K rows per quarter) |

## Annual Update Process

### 1. Download CMS files

**PFS (Physician Fee Schedule):**
- URL: https://www.cms.gov/medicare/payment/fee-schedules/physician/carrier-specific-files
- Download the "Carrier-Specific" ZIP for the target year
- Process with `python scripts/process_pfs.py` to generate the CSV

**OPPS (Outpatient Prospective Payment System):**
- URL: https://www.cms.gov/medicare/payment/prospective-payment-systems/hospital-outpatient/addendum-a-b-updates
- Download Addendum B for the target year
- Process with `python scripts/process_opps.py` to generate the CSV

**CLFS (Clinical Laboratory Fee Schedule):**
- URL: https://www.cms.gov/medicare/payment/fee-schedules/clinical-laboratory/annual-lab-updates
- Download the national limit file for the target quarter
- Process with `python scripts/process_clfs.py` to generate the CSV

### 2. Load into Supabase

```bash
cd backend
source venv/bin/activate

# PFS — annual
python scripts/load_historical_rates.py \
    --schedule PFS --year 2025 --file data/pfs_rates_2025.csv

# OPPS — annual
python scripts/load_historical_rates.py \
    --schedule OPPS --year 2025 --file data/opps_rates_2025.csv

# CLFS — quarterly
python scripts/load_historical_rates.py \
    --schedule CLFS --year 2025 --quarter Q1 --file data/clfs_2025q1.csv
python scripts/load_historical_rates.py \
    --schedule CLFS --year 2025 --quarter Q2 --file data/clfs_2025q2.csv
python scripts/load_historical_rates.py \
    --schedule CLFS --year 2025 --quarter Q3 --file data/clfs_2025q3.csv
python scripts/load_historical_rates.py \
    --schedule CLFS --year 2025 --quarter Q4 --file data/clfs_2025q4.csv
```

### 3. Verify

Run these queries in the Supabase SQL Editor:

```sql
-- Check all loaded versions
SELECT schedule_type, vintage_year, vintage_quarter,
       effective_date, expiry_date, is_current, row_count
FROM rate_schedule_versions
ORDER BY schedule_type, effective_date;

-- Verify row counts match
SELECT v.schedule_type, v.vintage_year, v.row_count AS expected,
       COUNT(h.id) AS actual
FROM rate_schedule_versions v
LEFT JOIN pfs_rates_historical h ON h.version_id = v.id
WHERE v.schedule_type = 'PFS'
GROUP BY v.id
ORDER BY v.vintage_year;

-- Spot-check a specific code
SELECT h.hcpcs_code, h.carrier, h.locality_code,
       h.facility_amount, h.nonfacility_amount,
       v.vintage_year
FROM pfs_rates_historical h
JOIN rate_schedule_versions v ON v.id = h.version_id
WHERE h.hcpcs_code = '99213'
  AND h.carrier = '00510'
  AND h.locality_code = '00'
ORDER BY v.vintage_year;
```

### 4. Validate with a test request

```bash
# Bill with an old service date should trigger historical lookup
curl -X POST http://localhost:8000/api/benchmark \
  -H "Content-Type: application/json" \
  -d '{
    "zipCode": "33701",
    "serviceDate": "03/15/2025",
    "lineItems": [{"code": "99213", "codeType": "CPT", "billedAmount": 250}]
  }'
```

If historical data is loaded for 2025, the response will have `isHistorical: true`.
If not loaded yet, `historicalDataAvailable: false` and a warning message.

## Rollback

To remove a loaded version and all its rate data:

```sql
-- The CASCADE on the foreign key will delete all rate rows
DELETE FROM rate_schedule_versions WHERE id = '<version-id>';

-- If you need to also un-set the expiry on the previous version:
UPDATE rate_schedule_versions
SET expiry_date = NULL
WHERE schedule_type = 'PFS'
  AND vintage_year = 2024;  -- adjust as needed
```

## Dry Run

Validate a CSV without loading:

```bash
python scripts/load_historical_rates.py \
    --schedule PFS --year 2025 --file data/pfs_rates_2025.csv --dry-run
```

## Notes

- The loader script inserts in batches of 500 rows for reliability
- The `is_current` flag is NOT set by the loader — current-year rates
  are always served from in-memory CSVs for performance
- Loading PFS data (~841K rows) may take several minutes depending on
  network speed to Supabase
- The `expiry_date` on previous versions is automatically updated when
  a new version is loaded
