-- 047_payer_coverage_policy_sources.sql
-- Add payer coverage policy test sources to mmr-vaccine-autism topic.

INSERT INTO signal_sources (issue_id, title, url, source_type, publication_date, content_text, metadata)
SELECT
  id,
  'UnitedHealthcare Coverage Policy: Childhood Immunizations',
  'https://www.uhcprovider.com/content/dam/provider/docs/public/policies/comm-medical-drug/childhood-immunizations.pdf',
  'payer_coverage_policy',
  '2025-01-15',
  'UnitedHealthcare covers all ACIP-recommended childhood immunizations including MMR vaccine without prior authorization. Coverage applies to all plan types. No medical necessity review required for standard immunization schedule.',
  '{"slug": "uhc-childhood-immunizations", "payer": "UnitedHealthcare", "policy_type": "medical", "key_findings": ["MMR vaccine covered without prior auth", "ACIP schedule followed for all plan types", "No exemptions for non-medical reasons"]}'::jsonb
FROM signal_issues WHERE slug = 'mmr-vaccine-autism';

INSERT INTO signal_sources (issue_id, title, url, source_type, publication_date, content_text, metadata)
SELECT
  id,
  'Aetna Clinical Policy Bulletin: Vaccines and Toxoids',
  'https://www.aetna.com/cpb/medical/data/1_99/0070.html',
  'payer_coverage_policy',
  '2025-03-01',
  'Aetna considers all ACIP-recommended vaccines medically necessary. MMR vaccine is covered for all age-appropriate members. Aetna does not consider the discredited Wakefield study or anti-vaccine claims as valid basis for coverage denial or alternative scheduling.',
  '{"slug": "aetna-vaccines-toxoids", "payer": "Aetna", "policy_type": "clinical_policy_bulletin", "key_findings": ["MMR covered as medically necessary", "ACIP schedule is the coverage standard", "Wakefield study explicitly discredited in policy"]}'::jsonb
FROM signal_issues WHERE slug = 'mmr-vaccine-autism';

INSERT INTO signal_sources (issue_id, title, url, source_type, publication_date, content_text, metadata)
SELECT
  id,
  'Anthem Blue Cross: Preventive Care and Immunization Coverage',
  'https://www.anthem.com/preventive-care',
  'payer_coverage_policy',
  '2024-09-15',
  'Anthem covers preventive immunizations at 100% with no cost sharing when administered by in-network providers, in accordance with ACIP recommendations. MMR vaccination is included in standard preventive benefits for children and adults without prior immunity.',
  '{"slug": "anthem-preventive-immunizations", "payer": "Anthem Blue Cross", "policy_type": "preventive_care", "key_findings": ["100% coverage for ACIP-recommended vaccines", "No cost sharing for in-network administration", "MMR included in standard preventive benefits"]}'::jsonb
FROM signal_issues WHERE slug = 'mmr-vaccine-autism';
