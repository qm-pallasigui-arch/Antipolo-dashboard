# Prototype forecasting integration

PROTOTYPE ONLY. TODO THESIS-METHOD: Final forecasting algorithm and candidate model set are not yet approved.

`ForecastService.generate_forecast(user, block_id, horizon)` checks administrator authorization, a 1–12 month horizon, the active normalized dataset and the existing 8/8 + 96 eligibility service before invoking an adapter. Ineligible blocks never reach inference. Views and reports also suppress stored forecasts for ineligible blocks. Historical JSON files never enter active storage automatically.

The default adapter calls `forecast_series(values, h=horizon)` in the supplied wrapper. The wrapper depends on an external `icd_forecast` module, absent from the supplied assets. Provide that implementation and its dependency requirements before live inference can be verified. This revision deliberately does not invent or replace its tuning, rolling evaluation or residual-learning algorithms. The root `icd_inference.py` remains a developer CLI facade; use `python -m dashboard.monthly.forecasting.icd_inference --series series.json` as an alternative. Developer CLI execution does not establish primary-dashboard eligibility.

The adapter receives the full classified calendar series. It passes reported consultation counts chronologically to the flat-series prototype, omitting unavailable months without imputing them. This compresses the 2020/2022 calendar gaps and is disclosed in saved warnings. No final missing-year policy is implied; original dates and nulls remain intact in the dataset and charts.

The normalized contract contains trusted run ID, dataset signature, ICD-10 block, cutoff, creation timestamp, prototype/is_prototype flags, model label, observation count, horizon, selected_output.forecast, calendar forecast_values with consultation_count, model_metadata, evaluation, warnings and status. Completed prototype runs use model_status=prototype_available; failures use failed and preserve the previous completed run. Changed dataset signatures do not reuse old forecasts. No raw Prophet/hybrid payload or cases field reaches the frontend.

When the correction weight is zero, the learner abstains, or correction fails, the adapter selects the base forecast and marks corrector_applied=false. It never claims a hybrid improvement. Available CV MAE is labeled Prototype evaluation, without claiming it is a finalized metric or assigning it to unreported horizons. Technical engine details are shown in the administrator insights view; regular forecasts use Prototype Forecast.

All current engine outputs include the required prototype disclaimer. Reports carry the disclaimer in HTML, JSON and forecast CSV rows. Completion/failure notifications explicitly identify prototype runs. Final Method Mode remains reserved and has no implementation.

Replacement adapters implement `generate(observations, horizon)` and return the generic contract; they need no Prophet fields or residual learner. The obsolete research-engine compatibility protocol was removed during cleanup; adapters use only this generic interface. Final engine installation and approval are future work.

Fixtures `icd_inference_a00.json` (96 observations) and `icd_inference_b25.json` (84) are supplied historical outputs for developer tests. A00-A09 is a preferred demo only after active eligibility validation. B25-B34 is descriptive-only at 84 observations even though its historical fixture contains forecasts.

Run `python -m pytest tests/test_monthly_system.py tests/test_prototype_forecast.py -q` to verify normalization, abstention/fallback, gating, persistence, invalid output rejection, reports, terminology, labels and model-independent replacement. These tests do not validate forecasting accuracy.

Verification on October 26, 2026: full regression suite 365 passed; final focused monthly/prototype suite 35 passed. Pyflakes and git diff whitespace checks passed. Windows pytest runs required execution outside the sandbox because its temporary directories returned access-denied errors. Live inference and browser visual validation were not performed for this addendum; the missing engine dependency remains a blocker for live inference.
