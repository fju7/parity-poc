# Changelog

## Session M — 2026-03-16

### Smoke Test Verifications (Item 1)
All 5 checks passed with no fixes needed:
- 1a: No remaining `$149` text in employer frontend
- 1b: BrokerConnectCard admin email includes requester name, email, company, and benchmark data
- 1c: Provider saved-rates endpoint returns all saved payers for an account
- 1d: Health UploadView has text paste textarea with Analyze button
- 1e: Signal SummaryThemeSection and DebateItem both have `bg-white` contrast fix

### Data Freshness Audit (Item 2)
Audited all reference data tables in Supabase:
- `pharmacy_nadac`: 24,866 rows, effective dates 2021-02-01 to 2022-02-09
- `ncci_edits`: 2,210,396 rows, effective dates 1996-01-01 to 2026-01-01
- `provider_benchmark_observations`: 99 rows, all from 2026-03-14
- No tables found for: mue_values, asp_pricing, clfs_rates, pfs_rates, opps_rates

### Migration 041: data_versions table (Item 3)
- Created migration file: `backend/migrations/041_data_versions.sql`
- Table tracks: data_source, version_label, effective_from/to, loaded_at, next_update_due, record_count, notes
- Fred action required: run migration + INSERT statements in Supabase SQL Editor

### Staging Environment (Item 4)
- Deferred: CLAUDE.md forbids branch creation, and CivicScale_Staging_Setup_Guide.docx not found in repo
- Awaiting Fred's confirmation before creating staging branch

### Files Changed
- `CLAUDE.md` — added Session M notes, updated migration list (next: 042)
- `CHANGELOG.md` — created
- `backend/migrations/041_data_versions.sql` — new migration
