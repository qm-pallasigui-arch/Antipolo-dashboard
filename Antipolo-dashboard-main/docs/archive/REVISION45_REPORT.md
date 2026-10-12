# Revision 45 reconciliation and implementation handoff

Date: 3 October 2026, Asia/Manila.

## Outcome

**Exploratory Weekly Configuration v0.1 — Technical / Retrospective Evaluation Only** is now the installed default. This implements Decisions 44–45 from the supplied final handoff. It supersedes today's earlier statements that no default protocol exists. It is not final adviser-approved methodology and does not establish real-data accuracy.

The supplied handoff is preserved at `docs/APPROVED_HANDOFF_REVISION45.md`. Its final section ends at “Unless separately”; no missing continuation was invented.

## Implemented changes

| Decision / requirement | Implementation |
| --- | --- |
| Exploratory protocol | Exact 16 supplied SARIMA candidates with m=52; candidate selection by finite AIC subject to convergence/validity checks. Failed candidates remain in diagnostics. |
| NNAR | Residual lags 1,2,3,4,52; one hidden layer, 3 nodes; maximum 2,000 iterations; seed 42; training-only standard scaling and recursive prediction. |
| Minimum history | 156 usable observations required for each fit, including the pre-holdout fit. This is a technical minimum, not a sufficiency claim. |
| Evaluation | Final 52 modeled positions form a single chronological holdout. Models use identical finite actual positions. Advanced Details and exports include 1–4/13/26/52 scores and coverage. |
| Week 53 | Preserved in sequence; exploratory m=52 warning retained in results. No remapping, merging, or automatic deletion. |
| Missing counts | Source values stay unchanged unless explicitly resolved with evidence. State-space missing handling and complete NNAR lag windows remain enforced. |
| Decision 41 | Historical reporting period complete is available as a dataset-level declaration; a source documentation reference is required. Row-level incomplete statuses still take precedence. |
| Decision 42 | Each blank may be explicitly resolved as zero, missing, corrected count, or nonexistent week, with a source reference. Original record, timestamp, decision, and reference are retained. Re-preparation reapplies decisions. |
| Decision 43 | New year-length declarations require a source calendar reference. Nonexistent-week exclusion requires a blank week-53 record and documented 52-week year. Other source-calendar conflicts remain blocked. |
| Worksheet refinements | Detected layout/status and year columns are displayed; inferred worksheet Disease has a Change disclosure. Changed mappings require preparation before confirmation. |
| Evidence and isolation | Exploratory label appears in Forecast/Advanced Details and exports. Synthetic context is retained. Forecast cache version advanced to weekly-2. |

## Explicit implementation choices

The handoff did not specify every technical safeguard. These choices are recorded in configuration: no deterministic trend; residual burn of 53 positions; minimum 52 complete residual training examples; diagnostic lag 52; SARIMA optimizer limit 300; existing ReLU/standard-scaler/LBFGS/alpha=1 behavior. They are implementation choices for exploratory operation, not adviser-approved rules.

The separate SARIMA comparison uses the lowest-AIC successful candidate. Hybrid attempts permitted successful candidates in ascending AIC until a valid NNAR correction succeeds. Both selected base configurations are exported; they can differ when a lower-AIC candidate cannot support NNAR. Uncertainty remains provisional training-residual-RMSE shading. No rolling-origin evaluation or calibrated 95% interval was added.

## Full protocol execution — synthetic verification only

`python tests/verify_revision45.py` ran the actual 16-candidate protocol on 312 seeded synthetic weekly observations, with a 52-position holdout and documented synthetic calendar. It took approximately **433 seconds** on this machine. Both models produced 52-point future paths and all four horizon evaluations. This runtime is evidence for one fixture, not a performance guarantee.

| Model | Holdout MAE | Holdout WAPE |
| --- | ---: | ---: |
| Hybrid SARIMA–NNAR | 2.627749 | 8.675743% |
| SARIMA-only | 2.236039 | 7.382478% |

SARIMA-only performs better on this fixture. That result is preserved without tuning the fixture or changing the authorized model set to make Hybrid win. These numbers are not Antipolo accuracy estimates or thesis validation.

Full parameters, candidate outcomes, training index, evaluation coverage, and metrics: `evidence/revision45/synthetic-full-protocol.json`.

## Current surveillance workbook: real next steps

Freshly checked with the installed exploratory protocol: 1,590 observations, 9 blank counts, and 30 supplied week-53 records; no activation errors. Notes remains excluded. All three disease runs correctly stop with **No complete, reported weeks available for training**, because source completeness is not established. Calendar year lengths also remain unknown. Evidence: `evidence/revision45/source-readiness.json`.

To proceed:

1. Obtain CESU/source confirmation of historical reporting completeness. In review, set Historical reporting period complete and supply the document reference only if supported.
2. Obtain the 52/53-week reporting calendar for relevant years and supply its reference. A fixed exploratory seasonal period of 52 does not establish those source calendars.
3. Resolve each of the 9 blanks individually using source evidence. Keep unreported values missing. Exclude a nonexistent week only under the documented calendar condition. Original source records remain available.
4. Update Data Summary, review revised observations and decisions, and Confirm & Use Data.
5. Generate Forecast. Both 52-week trajectories and held-out scores will be computed where data and convergence permit. Hybrid failure remains explicit; SARIMA is never relabeled.
6. Preserve the source decisions and exported results. Final thesis eligibility still separately requires ages 5–19, confirmed-only cases, approved disease coverage, CESU/PIDSAR provenance, and approved methodology.

The two warnings are handled deliberately: blank counts are not zero; supplied week 53 is preserved. They do not by themselves block activation, but calendar conflicts and unusable training data can block modeling. Detailed recovery guidance is in the application and `RECONCILIATION_HANDOFF_2026-10-03.md`; its earlier pending-protocol status is superseded here.

## Verification and handoff

New acceptance coverage: `tests/test_revision45.py`. Real seasonal execution: `tests/verify_revision45.py`. Desktop/mobile browser workflow: `tests/browser_revision39.py` (13 checks, no page errors); worksheet workflow: `tests/browser_worksheets.py` (7 checks, no page errors). The individual source-backed blank-resolution screenshot was visually inspected.

README, WEEKLY_SYSTEM, forecast/transformation reports, and current handoff pointers are updated. Previous evidence and uncommitted work are preserved. No final adviser approval, real-source correction, prospective validation, or deployment is implied.


## Final Revision 45 verification ? 2026-10-03

`python -m pytest -q`: **221 passed**, 10 existing Dash DataTable deprecation warnings, 61.76 seconds. Both browser suites passed (13 workflow checks + 7 worksheet checks), no page errors. Pyflakes and diff whitespace checks passed. Full 16-candidate seasonal synthetic run completed with both 52-point model paths and all four horizon scores. See `evidence/revision45/verification-summary.json` and `REVISION45_REPORT.md`.

## Reporting-completeness recovery follow-up

Added Data → Update Source Information to stage an editable copy of the active dataset without re-uploading. Source-backed declarations still require documentation; Cancel preserves active data, and confirmation applies changes. The no-complete-weeks message now gives these next steps explicitly. Mapping/re-inclusion uses the staged dataset's own original source to prevent stale-upload reuse. Focused verification: 52 tests passed; pyflakes passed.
