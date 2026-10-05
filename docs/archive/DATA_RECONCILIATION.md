# Source-data reconciliation — 27 September 2026

The supplied workbook faithfully transcribes **all 1,590 weekly PDF cells**, including nine source dashes retained as workbook blanks. This establishes transcription agreement, not epidemiological completeness or eligibility for ages 5–19 confirmed-case research. **Dengue 2024 remains unresolved: the PDF prints 4,516; its weekly observations sum to 4,588; the workbook follows 4,588 (difference +72).** No original file was edited.

## Reproduction and evidence

Run `python reconciliation/source_reconcile.py` from the repository root with the four byte-identical original sources bundled in `reconciliation/sources/` (parent Downloads is a fallback). The run completed successfully on 27 September 2026 using installed `pdfplumber`, `openpyxl`, and the application parser. The script extracts PDF cells independently of the workbook, compares each source cell to its workbook coordinate, calculates annual totals independently, reproduces the provisional calendar transformation with Python's standard-library calendar, and compares all 360 monthly rows to the application parser. Assertions fail on cell or monthly discrepancies. Rendering was used to visually verify table geometry and the printed Dengue discrepancy.

- `reconciliation/source-weekly-cell-comparison.csv`: all 1,590 comparisons, workbook coordinates, PDF page and row coordinate where applicable, raw source cell, numeric value, and provisional month mapping.
- `reconciliation/source-annual-reconciliation.csv`: all 30 disease/year totals, PDF printed totals, independent PDF weekly sums, workbook weekly sums, workbook formula and cached result, blanks, explicit zeros, difference, status, and follow-up.
- `reconciliation/source-monthly-independent.csv`: 360 independently aggregated source monthly observations with the combined Measles-Rubella label preserved.
- `reconciliation/source-reconciliation.json`: source hashes, exact paths, counts, annual table, workbook Notes text, and parser output labels/notes.
- `reconciliation/source-*-text.txt`: direct PDF extraction evidence; text order is imperfect on the two complex tables, so the script uses PDF glyph coordinates for those tables.
- `reconciliation/source-measles.png` and `source-dengue-page2.png`: rendered originals used to inspect the table geometry and totals visually.

## Source identity and provenance

| Source | SHA-256 |
|---|---|
| Antipolo_Disease_Surveillance_2016-2025.xlsx | `c8e90c7e040e0c5e5b4676bbe6e26485e6921054d89f684f4f3768ae43cb73ff` |
| Distribution of Dengue Cases per Morbidity Week of Antipolo City, Rizal from year 2016-2025.........pdf | `b581387a11d822148c750291d45e5af6570059fb38bd41e097e13be050508955` |
| Distribution of Measles-Rubella Cases per Morbidity Week of Antipolo City, Rizal from year 2016-2025.pdf | `c2d42390a6b94158b3dd830da3308ca92cec361e5a445f92b8a6fa31459d658a` |
| LEPTO 2016-2025 ANTIPOLO.pdf | `396c1bb1a93cd4c70639ed3bc4486121d772f933f61db53fc0a9bb1a5035ba74` |

The Dengue PDF has two pages; Measles-Rubella and Leptospirosis have one each. Dengue and Measles-Rubella identify DOH CHD CALABARZON, RESU, the Philippine Integrated Disease Surveillance and Response (PIDSR) Information System, and a prepared date of August 5, 2026. The Leptospirosis PDF provides its disease/location/2016–2025 table title but no equivalent printed annual total or source-system provenance statement. None of these three tables contains age, enrollment, or case-classification fields. The author identifies them as all-age surveillance; the report contents do not independently establish a confirmed-only definition. File hashes identify reviewed bytes; they do not authenticate the source office or attest completeness.

The workbook has three disease sheets and a Notes sheet. Each disease has weeks 1–53 and years 2016–2025; Measles-Rubella columns were reversed from the PDF's descending years into ascending workbook years. The workbook SUM formulas and stored cached totals agree with independently summed weekly values. The Notes sheet's claim that Dengue printed and computed totals “match” is false for 2024. Preserve that original statement as evidence and use the explicit reconciliation above.

## Annual totals

Cells below give PDF printed total / weekly PDF sum / workbook weekly sum. A dash means no printed total exists, not zero cases. The annual CSV contains the full required verification status and follow-up for every row.

| Year | Leptospirosis | Measles-Rubella | Dengue |
|---|---|---|---|
| 2016 | — / 2 / 2 | 51 / 51 / 51 | 1127 / 1127 / 1127 |
| 2017 | — / 4 / 4 | 64 / 64 / 64 | 1004 / 1004 / 1004 |
| 2018 | — / 14 / 14 | 644 / 644 / 644 | 2593 / 2593 / 2593 |
| 2019 | — / 6 / 6 | 1519 / 1519 / 1519 | 2312 / 2312 / 2312 |
| 2020 | — / 5 / 5 | 27 / 27 / 27 | 503 / 503 / 503 |
| 2021 | — / 3 / 3 | 8 / 8 / 8 | 1011 / 1011 / 1011 |
| 2022 | — / 16 / 16 | 26 / 26 / 26 | 2138 / 2138 / 2138 |
| 2023 | — / 124 / 124 | 51 / 51 / 51 | 4274 / 4274 / 4274 |
| 2024 | — / 87 / 87 | 55 / 55 / 55 | **4516 / 4588 / 4588** |
| 2025 | — / 111 / 111 | 110 / 110 / 110 | 5542 / 5542 / 5542 |

All 30 workbook annual sums agree with PDF weekly sums. Nineteen of the twenty printed PDF annual totals agree; Dengue 2024 differs. No printed Leptospirosis total exists, so it would be incorrect to describe its independently computed sum as a verified printed total. CHO must identify the correct Dengue total and any affected weekly cells; this audit does not choose a correction or attribute the difference to a specific week.

## Blanks, explicit zeros, and week 53

There are 1,581 numeric cells, including **636 explicit zeros**, and nine blank workbook cells. No week row 1–53 is absent. Weeks 1–52 have numeric values in all three diseases and ten years. The nine blanks are exclusively Dengue week 53 in 2016–2024; their PDF cells contain a dash. A dash could mean not applicable, not reported, or another office convention; it must not be silently reclassified as an observed zero. Dengue week 53 of 2025 is explicitly 56.

Leptospirosis week 53 is explicitly zero in every year. Measles-Rubella week 53 is explicitly two in 2023, five in 2025, and zero in all other years. These source observations remain preserved even when Python's ISO calendar rejects that year's week 53.

The supplied source has no negative, fractional, or non-numeric weekly case values apart from the nine recognized source dashes/workbook blanks. This absence of arithmetic invalidity does not show that surveillance was exhaustive during lockdowns, low-count periods, or any other interval.

## Provisional weekly-to-monthly conversion

`dashboard/data/xlsx_parser.py:30` assigns each valid ISO week to the calendar month containing its Thursday. When ISO rejects week 53, the code assigns it to December of the reporting year. Within 2016–2025, 2020 is the only year with an ISO week 53. Non-ISO week 53 values therefore use the fallback in the other years. This includes the seven Measles-Rubella cases in 2023/2025 and 56 Dengue cases in 2025; zero-valued week 53 cells also retain their dates. The 2020 Dengue week 53 remains blank despite being an ISO-valid week, underscoring the need for office clarification.

The independent check produced 120 months per disease, January 2016–December 2025, with no absent monthly keys. All 360 provisional monthly values match the application parser and conserve the 30 annual sums. These values are **week-assigned monthly totals**, not necessarily case-onset calendar-month totals. A complete monthly key grid can hide missing weekly observations and does not establish epidemiological completeness. Official week start/end rules, year crossover, week 53 meaning, and use of onset/report date remain awaiting CHO confirmation.

## Dataset-to-research matrix

| ID | Research requirement | Actual source evidence | Eligibility | Required action |
|---|---|---|---|---|
| D01 | Ages 5–19, city-wide, intended to inform public-school preparedness | Three disease PDFs contain weekly all-age totals per author; no ages or enrollment fields | Ineligible as proof for ages 5–19 | Obtain age-stratified extract; do not estimate ages from proportions or claim school acquisition/enrollment |
| D02 | Confirmed cases only | No classification fields or confirmed-only statement in these tables | Unverified | CHO supplies inclusion definitions and confirmed-only extract |
| D03 | Preserve all-age analysis separately | Workbook matches supplied all-age tables arithmetically | Eligible only for separately labeled provisional all-age evaluation | Keep findings separate from future eligible-age evaluation |
| D04 | Preserve combined Measles-Rubella provisionally | PDF title and workbook sheet explicitly combined | Provisionally allowed; final definition open | Retain source name; researcher/adviser/epidemiologist approve final category |
| D05 | Audit weekly and annual integrity | 1590/1590 cells match; 19/20 printed totals agree | Transcription verified, source contradiction unresolved | Preserve 4516 and 4588; request CHO correction |
| D06 | Approved monthly time basis | ISO Thursday plus December fallback is software convention, not source-confirmed | Provisional | CHO verifies calendar and week 53 semantics |
| D07 | No invented missing observations | Nine Dengue dashes/blanks; 636 observed zeros | Blank semantics unresolved | Preserve separately; no zero imputation or completeness claim |
| D08 | No synthetic/genuine mixing | `dashboard/data/combine.py:5` prepares uploaded records alone | Implementation supports separation; source audit did not inspect every UI transition | Use application tests for confirmation; label synthetic demonstration outputs separately |
| D09 | Population metadata does not self-certify eligibility | PDFs contain no row-level age/classification fields | Eligible ages 5–19 confirmed dataset unavailable | Verified eligibility requires source evidence; filename or user-entered labels alone are insufficient |
| D10 | Final disease set and operational horizon require expert input | Source availability supplies initial three categories, no operational horizon recommendation | Still deferred | CHO/expert interview; do not pivot to Top 5 or finalize horizon |

## Ingestion observations and limits

At initial inspection the workbook parser skipped blanks without a count, renamed Measles-Rubella to Measles through configuration, and clipped negative counts to zero; generic normalization also dropped invalid values and could sum duplicates before the duplicate check. These were reported to the application owner. The final successful reconciliation rerun observed the revised combined label, provisional calendar/population warnings, and nine explicit blank-observation warnings retaining unknown coverage. It verifies unchanged arithmetic on this source, not every malformed-upload rejection path. See TEST_RESULTS.md and the consolidated handoff for final regression results and exact changed-file inventory.

The original PDF converter (`dashboard/data/pdf_converter.py`) relies on automatic table detection; it detects neither the Measles-Rubella table nor Dengue page 2 reliably. The source-specific reconciliation script deliberately uses inspected glyph coordinates to avoid silently omitting these pages. Do not describe that independent audit script as a generalized production PDF-ingestion fix. The dashboard supports workbook ingestion; the supplied workbook itself passed the independent transcription check.

The audit preserves raw source files, source semantics, unfavorable discrepancies, and all-age limitations. It does not establish official CHO acceptance, confirmed-only coverage, age-specific model accuracy, report completeness, or real-world operational benefit.

Known missing weeks 1-52 or blank cells within those weeks now carry `coverage_status=incomplete` and block modeling. Week 53 ambiguity remains explicitly provisional to preserve the authorized conversion.
