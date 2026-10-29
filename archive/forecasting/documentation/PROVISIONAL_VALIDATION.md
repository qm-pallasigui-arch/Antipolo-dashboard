# Provisional Model Validation — Not Thesis-Validated

Restart `run.bat` (which runs `app.py` with the local virtual environment) or
restart your existing `python app.py` process. Refresh the browser. Upload and
activate your weekly dataset, select the disease, open Forecast, and choose
**Generate Forecast**. Unverified uploaded data automatically uses provisional
validation. This is a full search, much slower than Quick Preview. Progress shows actual candidate fits and stages;
there is no estimated completion percentage. Keep the Python server running.

The guided action replaces the former four-button workflow:

| Action | Parameters | Evidence |
|---|---|---|
| Generate Forecast, unverified upload | Full provisional search | Final Test and future path, explicitly provisional |
| Generate Forecast, research-eligible source | Existing applicable research lock, or full research selection | Compatible historical performance included automatically; approval never granted automatically |
| Advanced Options → Quick Preview — Fixed Settings | Fixed demonstration preset | Illustrative path only; no benchmark accuracy |

Unknown population, case classification and provenance do not block provisional
selection. Structural errors still do: duplicates, invalid counts, incompatible
reporting calendars, invalid chronology and insufficient history. Genuine zeros
are retained, blank counts remain missing, and Week 53 remains a separate
chronological observation. Explicitly incomplete reports are excluded. If
reporting completeness is unknown, provisional mode includes supplied rows under
an explicit recorded assumption. Unspecified historical year lengths use 53 when
the source supplies Week 53, otherwise 52; this is an assumption about source
positions, **not verification of a reporting calendar**. These assumptions appear
in the panel, signed configuration and report. Original source metadata and
research eligibility are unchanged. Unknown future calendar years use horizon
offsets, not invented calendar labels.

The last 52 chronological positions are Final Test, the preceding 52 are
Validation, and all earlier positions are Training. At least 156 observed
training positions and 52 complete residual lag examples are required. Missing
positions are never compressed; a missing terminal NNAR lag window prevents that
configuration from forecasting. Both holdout blocks need observed outcomes.

The shared estimator evaluates 144 SARIMA candidates: p,q in 0–2, d,D in 0–1,
P,Q in 0–1, s=52. All use a 108-position likelihood burn. The ten successful
lowest-AIC fits are compared on Validation RMSE, then MAE and supporting MAPE.
RMSE ties use the established relative tolerance 1e-6 and absolute tolerance
1e-8. SARIMAX is the statsmodels implementation class; with no exogenous inputs,
the fitted model is SARIMA.

NNAR evaluates 96 combinations of lags {2,4,6,8,13,26}, hidden nodes {2,4,8,12}
and alpha {.001,.01,.1,1}, each with seeds {42,137,2026}. It fits training-only
post-burn residuals, scales training lag inputs only, keeps targets unscaled,
and recursively predicts future residuals. The winner uses median Validation
Hybrid case-count RMSE, then MAE and supporting MAPE. All three seeds must
converge. Test and future refits use predeclared production seed 42. No candidate
is selected using the Final Test.

The configuration is signed and saved **before** the Training+Validation refit
and Final Test scoring. Afterwards, the same settings are refitted on all usable
history to produce one 52-week future path. The 4/13/26/52 views are slices.
There is no test-driven retuning. Historical algorithmic exclusion does not
erase any earlier human exposure to these historical outcomes.

The Forecast page displays Actual/SARIMA/Hybrid for the Final Test, historical
context, validation and test errors with coverage, peak and direction evidence,
ADF and adjusted Ljung–Box diagnostics, and expandable Forecast Components.
Hybrid = max(0, raw SARIMA + NNAR correction); the raw components are preserved.
No noise, copied peaks or amplitude adjustment is added.

Peak comparisons use identical observed test positions; ties use the earliest
position. Timing error is signed chronological position difference, including
Week 53. Direction agreement uses adjacent finite actual pairs only and does
not bridge gaps. A descriptive surge flag requires peak >= twice the median and
peak-minus-median >= 10 cases. It is flagged as missed when peak timing is off by
more than four positions or peak magnitude error exceeds 50% of actual peak.
The smoothness flag requires the forecast first-difference standard deviation
to be below half the actual value, using the same valid pairs. These documented
heuristics are not significance tests or proof of seasonality/accuracy.

Exports: choose **Download Methodology Report** under **Model Performance** for JSON containing
fingerprint, status, settings, splits, search summary, validation seed evidence,
Final Test observations/predictions, components, diagnostics, interpretation,
future path, warnings and run metadata. The normal detailed evidence export
also includes the active dataset. CSV exports explicitly identify provisional
results. Files are saved separately under `.weekly-models/provisional/<run-id>/`:
`search.json` (all attempted candidates), `locked.json`, `evaluation.json`,
`result.json`, and `report.json`. Research registry files are never written.
`report.md` provides a readable summary and the full future component path.
Sample runs do not write or replace provisional locks. A failed final refit
leaves the existing lock and completed historical evaluation available for
inspection; failed search candidates retain their reasons in `search.json`.
If Final Test initialization fails, `failure.json` records the failure and partial
evidence. No future forecast is generated. The repository workbook's Dengue run
encountered this limit at the blank 2024 Week 53; see the
[actual run assessment](../evidence/provisional-dengue-workbook/assessment.md).

For a reproducible local run using an exported evidence JSON or unchanged workbook:

```powershell
.venv\Scripts\python.exe scripts/validate_provisional.py path\to\evidence.json --disease Dengue --output evidence\my-provisional-run
```

Use the actual exported dataset to reproduce browser edits and source decisions.
Using the repository workbook cannot establish that it matches a browser session.
Final Test performance is historical evidence, not a guarantee of future outcomes
or thesis eligibility. The separately gated research selection workflow remains
necessary when the final verified dataset becomes available.
