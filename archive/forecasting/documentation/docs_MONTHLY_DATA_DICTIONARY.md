# Monthly data dictionary

Analytical unit: ICD-10 infectious-disease block × calendar month. Period: 2016–2025. Population: ages 5–19. Geography: Antipolo City, Rizal. Consultations are not necessarily confirmed cases or unique individuals.

| Field | Rule |
| --- | --- |
| dataset_id | First 16 characters of content signature |
| dataset_signature | SHA-256 of canonical observations and study provenance |
| year | Integer, 2016–2025 |
| month / month_number | Full English month name / integer 1–12 |
| icd10_block | Canonical infectious-disease range, e.g. A00-A09 |
| icd10_description | Source description with normalized whitespace; conflicts rejected |
| consultation_count | Integer ≥ 0 when reported; null when unavailable |
| observation_status | observed, observed_zero, city_report_unavailable, outside_annual_top5 |
| top5_present | Boolean annual report presence |
| source_year_available | False for 2020/2022; true for the eight available years |
| source_file | Original filename, never used as a filesystem destination |

Headers normalize to lowercase underscores. ICD-10 Block, ICD-10 Description and month_number aliases are supported. Months accept numbers, names and abbreviations. Code en/em dashes become hyphens. No fuzzy inference from disease names or the old schema occurs.

Null rows may be supplied with correct unavailable status or omitted and derived from annual presence. A reported annual entry requires 12 values; missing months cannot become outside-Top-5 periods. More than five blocks per year are rejected. Each supplied block needs historical observations. Uploaders must verify that transcription includes every source annual entry; software cannot recover omitted source entries.

Derived block fields: eligible, available_report_years, required_available_years (8), top5_year_count, required_top5_year_count (8), reported_month_count, required_reported_month_count (96), missing_years, missing_months, reason. Missing-month lists concern required available years, excluding separately disclosed unavailable city years. Eligibility counts distinct year/month pairs, never duplicate rows or model scores.

Annual history holds year, presence, status and annual_total. Absent years have null totals; present years sum 12 months. Future ranks are not inferred.

Metadata retains provenance, source bytes/hash, uploader/time, candidate ID, activation time, warnings and annotations. Signatures represent normalized content/provenance; candidate IDs distinguish uploads.

Forecast exports use observation_status=forecast, separate from the four-state source vocabulary. Runs store signature, block, cutoff, horizon, engine/model IDs, evaluation, values, timestamps, status and warnings. Failed runs preserve the latest completed result.

Notifications have type, title, message, severity, creation time, role/user audience and related module/record. Read timestamps are per user. Reports preserve the source/forecast snapshot used at generation.
