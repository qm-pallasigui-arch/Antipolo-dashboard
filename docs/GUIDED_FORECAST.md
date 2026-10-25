# Guided forecasting

Choose the disease and horizon, then **Generate Forecast**. The application
checks structural validity and research eligibility, verifies configuration
integrity, and selects the appropriate workflow. Historical performance appears
automatically; there is no separate performance button.

- Unverified uploaded data runs full provisional selection, Final Test and future
  refitting, labeled **Provisional Forecast — Not Thesis-Validated**.
- Eligible research data uses its installed lock, otherwise an applicable runtime
  research lock. If neither exists, it runs full research selection and persists
  an immutable lock before evaluating Final Test.
- Research selection does not grant adviser approval. Unapproved research results
  are labeled **Research Forecast — Adviser Approval Pending**.
- Synthetic data uses **Advanced Options → Quick Preview — Fixed Settings** only.
  Preview uses the unchanged demonstration preset and creates no validation lock.

Results are grouped into **Future Forecast**, **Model Performance**, and collapsed
**Diagnostics**. Methodology JSON is downloaded from Model Performance. Forecast
CSV uses Download Results; detailed dataset evidence remains available under
About the Model. Open Reporting for the existing briefing and PDF export. Every
export retains the result's evidence status. Diagnostics include original split
boundaries, parameters, seed policy, ADF/Ljung–Box, peak/direction evidence, raw
SARIMA and NNAR correction paths, warnings and completed progress events.

## Historical evidence lifecycle

The lock records the original Training/Validation/Final Test periods. Appending
weeks never moves those periods. Compatible completed performance is reused, while
operational forecasting refits the locked settings on all current eligible history.
Changing the horizon only slices the generated 52-week path.

Compatibility hashes include historical values and missing masks, preparation
rules, disease, lock, model/methodology versions and boundaries. Revised Final
Test outcomes trigger evaluation on the original window and record that revision.
Changed Training/Validation observations or preparation rules stop forecasting.
Legacy metrics without sufficient evidence are recomputed only when the original
locked history is verifiable. An unsupported model version is not silently upgraded.

New research artifacts live under `.weekly-models/research/`, separate from
provisional artifacts and the administrator-maintained registry. Each source has
a selected-lock reference, immutable lock and original snapshot, fingerprinted
performance records and per-attempt lifecycle/result records. Installed locks
have their own namespace keyed by lock ID. Research registry files are never
automatically overwritten. Selection, evaluation and forecasting completion are
tracked independently: retrying a failed evaluation reuses its selected lock and
does not select new parameters. Approval fields remain unchanged.

Failures retain earlier successful results and available diagnostics, with an
explicit new-attempt failure message. No failure launches Quick Preview, changes
the missing-data policy, or adds residual warm-up. The unchanged repository
workbook's Dengue Week 53 initialization failure remains expected. A worse Hybrid
RMSE/MAE/MAPE is reported honestly and does not cause failure.

Restart the existing `run.bat` or `python app.py` process and refresh the browser
after updating. Old sample/provisional/research jobs and results remain readable;
legacy button names are replaced only in the current interface.
