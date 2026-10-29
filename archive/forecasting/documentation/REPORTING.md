# Reporting module

Reporting is a separate page for city health officers. Generate a Hybrid forecast in Forecast, then open Reporting, select a disease and choose 4 (default), 13, 26 or 52 weeks. Generate Report creates the on-screen briefing; Export PDF downloads the same content as a formal, paginated A4 document.

The baseline is the chronologically latest complete, nonmissing observed week for the selected disease. Every projected week compares against this fixed baseline. Percentage changes are unavailable for a zero baseline. Calculations use unrounded predictions; displayed values use one decimal place. Above-baseline weeks are highlighted, not labelled outbreaks or protocol-defined alerts. The outlook starts at the forecast cutoff, which may precede today's date.

Reports include scope, source date, forecast issue time, executive summary, a chart, all weekly values, four-week narrative blocks, suggested activities, proposed teams, timing, indicators, references and limitations. Reporting maintains independent disease and horizon controls. Dataset, disease, horizon or forecast changes clear the generated report and disable export. The export callback also rechecks all report contents against the current forecast before downloading.

`dashboard/weekly/reporting.py` provides deterministic calculations, the curated guidance registry and PDF rendering. `reporting_ui.py` provides the standalone page and callbacks. ReportLab is required for PDF generation and is included in both dependency manifests. No external AI service is used, and report data are not sent to DOH sites.

## Guidance coverage

The registry contains official DOH guidance for Dengue, Measles-Rubella and Leptospirosis:

- [DOH CAR: Dengue surveillance and response coordination / Enhanced 4S](https://caro.doh.gov.ph/coordination-meeting-and-situation-updating-in-connection-with-dengue-surveillance-and-response/)
- [DOH NIP Booklet 2, Chapter 3, E.2: Vaccine-Preventable Disease Surveillance](https://doh.gov.ph/wp-content/uploads/2023/08/Booklet-2-Vaccine-Preventable-Diseases-and-Vaccine-Preventable-Disease-Surveillance.pdf)
- [DOH Ilocos: Leptospirosis prevention advisory, August 27, 2026](https://ro1.doh.gov.ph/?p=4279)

These are guidance summaries, not a complete machine-readable DOH response protocol. Timing, teams and indicators are identified as application suggestions. Measles notification/investigation conditions refer to actual suspected cases. Leptospirosis exposure advice is conditional on documented exposure. Forecasts never automatically prescribe prophylaxis, fogging or outbreak response. No Antipolo-specific protocol or numerical action threshold is configured. Unsupported diseases retain forecast interpretation and show an explicit guidance gap instead of invented disease-specific interventions. Guidance updates require source review and a code change.

## Validation

Run `.venv/Scripts/python.exe -m pytest tests/test_reporting.py tests/test_weekly_views.py -q`.

For browser validation, run the app on port 8073 with debug disabled, then run `.venv/Scripts/python.exe tests/browser_reporting.py`. This requires Playwright and Edge. The browser test uses synthetic fixture predictions; it verifies reporting without refitting the forecasting model. Screenshots and the sample PDF are saved under `evidence/reporting/`.
