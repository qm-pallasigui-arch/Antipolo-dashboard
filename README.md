# Antipolo weekly infectious disease forecasting

A Dash application for weekly reportable infectious disease case counts among individuals aged **5–19 in Antipolo City**, using eligible **confirmed-only CESU/PIDSAR** surveillance records to support public-school preparedness.

Run `python app.py` and open the displayed URL. Install the project dependencies from `requirements.txt` first if needed. Production WSGI remains `app:server`; `/healthz` is the health endpoint.

The dashboard has five sections: **Overview**, **Forecast**, **Historical Trends**, **Data**, and **About the Model**. In Data, upload a CSV/XLSX. Recognizable columns and legacy week-by-year worksheets are prepared automatically. A **Review Data Transformation** popup compares the original and prepared records. Resolve any ambiguous columns using dropdowns, then **Confirm & Use Data**. Cancelling keeps the current dataset. No JSON editing or manual file restructuring is required for recognized layouts.

Hybrid SARIMA–NNAR is the primary model; SARIMA-only is a separate comparison. The installed Decision 90 protocol uses a fixed 144-candidate SARIMA grid, three expanding validation windows, a union of AIC shortlists, and a 20-configuration NNAR grid with five deterministic fits. Selected configurations are locked before final 52-week holdout evaluation, then refitted on full history for one future path. The 4/13/26/52-week views do not retrain. At least 364 calendar positions are required. No uncertainty interval is displayed. Model selection runs in a background job with progress, cancellation, and persistent result caching. The first full search remains computationally intensive. See [worker setup](docs/FORECAST_JOBS.md), including the persistent worker required for Vercel. Unknown reporting completeness or calendars still block fitting.

Missing weeks and blank counts are never zero-filled or automatically imputed. Week 53 is preserved. Incomplete or unknown reporting weeks remain visible and are excluded from training. All-age/unverified data are labeled Technical / Retrospective Evaluation. Synthetic / Demo Data cannot qualify as thesis evidence. Measles and Measles-Rubella remain distinct.

Read [WEEKLY_SYSTEM.md](WEEKLY_SYSTEM.md) for the input/metadata schema, eligibility gate, protocol fields, missing-data behavior, scoring coverage and limitations, exports, and future prospective snapshot/reconciliation workflow. Prospective validation is not yet completed. Monthly/quarterly summaries are display-only and require source-established week dates.

See [REVISION39_REPORT.md](docs/archive/REVISION39_REPORT.md) for the guided-workflow reconciliation and real-browser review evidence.

```powershell
python -m pytest -q
python -m pyflakes dashboard/weekly
```

The operational implementation is `dashboard/weekly/`. Earlier monthly modules and evidence remain preserved for historical regressions and audit purposes; they are not loaded by normal application startup. Pre-weekly documentation is archived under [docs/historical-pre-weekly](docs/historical-pre-weekly). Earlier handoffs and manuscript/audit documents describe historical work and are superseded by the weekly operational contract where they conflict.


Current implementation and evidence: [Decision 90 integration](docs/DECISION90_IMPLEMENTATION_STATUS.md). Source-backed completeness, calendar declarations, and individual blank-count decisions are available in the review. Original evidence is retained.

Documentation is organized in the [documentation map](docs/README.md). Historical handoffs and individual revision reports live under `docs/archive/`.
