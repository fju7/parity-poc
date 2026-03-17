-- 046_seed_cpt_mappings.sql
-- Seed CPT code to Signal topic mappings for the 20 highest-volume
-- Medicare CPT codes that map to existing Signal topics.

-- GLP-1 drugs (obesity/diabetes management)
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('99213', 'glp1-drugs', 0.70, 'Office visit level 3 — common for GLP-1 prescribing and management'),
('99214', 'glp1-drugs', 0.75, 'Office visit level 4 — complex medication management including GLP-1 titration'),
('99215', 'glp1-drugs', 0.65, 'Office visit level 5 — complex obesity/diabetes management'),
('96372', 'glp1-drugs', 0.90, 'Therapeutic injection, subcutaneous — GLP-1 agonist administration'),
('99211', 'glp1-drugs', 0.50, 'Office visit level 1 — nurse-led GLP-1 follow-up'),
('83036', 'glp1-drugs', 0.80, 'Hemoglobin A1c — primary monitoring for GLP-1 diabetes treatment'),
('80053', 'glp1-drugs', 0.60, 'Comprehensive metabolic panel — baseline/monitoring for GLP-1 therapy');

-- Breast cancer therapies
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('96413', 'breast-cancer-therapies', 0.95, 'Chemotherapy IV infusion first hour — CDK4/6 inhibitors, ADCs'),
('96415', 'breast-cancer-therapies', 0.90, 'Chemotherapy IV infusion each additional hour'),
('96417', 'breast-cancer-therapies', 0.85, 'Chemotherapy IV infusion each additional sequential infusion'),
('77263', 'breast-cancer-therapies', 0.80, 'Radiation treatment planning, complex — breast cancer RT'),
('19301', 'breast-cancer-therapies', 0.85, 'Mastectomy, partial — breast-conserving surgery'),
('38525', 'breast-cancer-therapies', 0.75, 'Biopsy or excision of lymph nodes — sentinel node biopsy'),
('88305', 'breast-cancer-therapies', 0.70, 'Surgical pathology level 4 — breast tissue examination');

-- Diet and breast cancer
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('97802', 'diet-and-breast-cancer-risk-prevention-and-recurrence', 0.85, 'Medical nutrition therapy initial — dietary counseling for cancer prevention'),
('97803', 'diet-and-breast-cancer-risk-prevention-and-recurrence', 0.85, 'Medical nutrition therapy subsequent — ongoing dietary management'),
('99401', 'diet-and-breast-cancer-risk-prevention-and-recurrence', 0.70, 'Preventive counseling 15 min — lifestyle/diet modification');

-- CAR-T cell therapy
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('0537T', 'car-t-cell-therapy', 0.95, 'CAR-T cell therapy, harvesting'),
('0538T', 'car-t-cell-therapy', 0.95, 'CAR-T cell therapy, preparation/infusion'),
('96413', 'car-t-cell-therapy', 0.70, 'Chemotherapy IV infusion — lymphodepleting conditioning'),
('36511', 'car-t-cell-therapy', 0.80, 'Therapeutic apheresis — T-cell collection');

-- CRISPR gene therapy
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('0537T', 'crispr-gene-therapy', 0.75, 'Cell therapy harvesting — applicable to gene-modified cell therapies'),
('0538T', 'crispr-gene-therapy', 0.75, 'Cell therapy preparation — applicable to gene-modified cell therapies'),
('81479', 'crispr-gene-therapy', 0.80, 'Unlisted molecular pathology procedure — genomic analysis for gene therapy eligibility');

-- MMR vaccine
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('90707', 'mmr-vaccine-autism', 0.95, 'MMR vaccine — measles, mumps, rubella live virus'),
('90710', 'mmr-vaccine-autism', 0.90, 'MMRV vaccine — measles, mumps, rubella, varicella'),
('90460', 'mmr-vaccine-autism', 0.70, 'Immunization admin first component — vaccine administration');

-- mRNA vaccine myocarditis
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('91300', 'mrna-vaccine-myocarditis', 0.95, 'Pfizer-BioNTech COVID-19 vaccine'),
('91301', 'mrna-vaccine-myocarditis', 0.95, 'Moderna COVID-19 vaccine'),
('93306', 'mrna-vaccine-myocarditis', 0.80, 'Echocardiography, complete — cardiac evaluation post-vaccine'),
('93000', 'mrna-vaccine-myocarditis', 0.75, 'Electrocardiogram, 12-lead — myocarditis screening'),
('93017', 'mrna-vaccine-myocarditis', 0.70, 'Cardiovascular stress test — cardiac follow-up');

-- Social media and teen mental health
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('90837', 'social-media-teen-mental-health', 0.80, 'Psychotherapy 60 min — adolescent mental health treatment'),
('90834', 'social-media-teen-mental-health', 0.80, 'Psychotherapy 45 min — adolescent mental health treatment'),
('90847', 'social-media-teen-mental-health', 0.75, 'Family psychotherapy with patient — social media impact counseling'),
('96127', 'social-media-teen-mental-health', 0.85, 'Brief emotional/behavioral assessment — PHQ-A, screen time assessment'),
('99213', 'social-media-teen-mental-health', 0.55, 'Office visit level 3 — adolescent wellness/mental health visit');

-- Health impacts of climate change
INSERT INTO signal_cpt_mappings (cpt_code, topic_slug, relevance_score, mapping_notes) VALUES
('99281', 'health-impacts-of-climate-change', 0.60, 'ED visit level 1 — heat-related illness'),
('99283', 'health-impacts-of-climate-change', 0.65, 'ED visit level 3 — respiratory exacerbation from air quality'),
('94010', 'health-impacts-of-climate-change', 0.70, 'Spirometry — pulmonary function testing for climate-related respiratory');
