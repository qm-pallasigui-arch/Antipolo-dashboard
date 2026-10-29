# Monthly canonical data

| Field | Meaning |
|---|---|
| year | Calendar year, 2016–2025 |
| month / month_number | Month name or 1–12 input; normalized calendar month |
| icd10_block | One of A00-A09, A15-A19, A80-A89, B00-B09, B25-B34, B85-B89, B90-B94 |
| icd10_description | Consistent source description |
| consultation_count | Nonnegative integer when observed, otherwise null |
| observation_status | observed, observed_zero, city_report_unavailable, outside_annual_top5 |
| source_year_available | City report available for that year |
| top5_present | Block represented in that annual source report |
| dataset_id / dataset_signature | Source dataset version and content signature |

City reports are unavailable for 2020 and 2022. Outside-Top-Five counts are unknown, not zero. Every reported annual block entry requires twelve numeric monthly observations. Duplicates, conflicting descriptions and more than five observed blocks per available annual source report are rejected.

Candidate summaries always include all seven blocks. Readiness states are not_assessed, ready, not_ready and methodology_configuration_required. No observations is a not_ready reason. Prototype readiness is explicitly provisional and uses the centralized technical settings; final readiness remains a Chapter 3 decision. top5_year_count and reported_month_count describe coverage. Missing-month diagnostics preserve the calendar and exclude unavailable city-report years from the available-year list.

Forecast runs store model name/version, dataset ID/signature, run/group ID, calendar origin, last observation cutoff, generation time, status, evaluation, warnings, is_prototype, methodology_status and configuration snapshot/hash. Each forecast month is independently stored in forecast_values with its hybrid and Prophet baseline values. Rankings link the group, source runs and dataset signature, with twelve-month totals and ranks. Fewer than five successful blocks produces top_five_status=unavailable and an empty top_five list while retaining all valid ranks. Neither output overwrites observations.
