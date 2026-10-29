"""Reproduce audit checks; seasonal-52 models are constructed, never fitted."""
import json
from pathlib import Path

import numpy as np
import statsmodels
from scipy.stats import chi2
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.statespace.sarimax import SARIMAX


def main():
    rng = np.random.default_rng(42)
    values = rng.normal(size=400)
    burn_checks = []
    for seasonal in ((1, 1, 1, 52), (2, 1, 1, 52)):
        model = SARIMAX(values, order=(2, 0, 0), seasonal_order=seasonal,
                        trend=None, enforce_stationarity=False,
                        enforce_invertibility=False)
        burn_checks.append({
            'order': [2, 0, 0], 'seasonal_order': list(seasonal),
            'loglikelihood_burn': model.loglikelihood_burn,
            'scored_observations': len(values) - model.loglikelihood_burn,
        })
    # Small genuine SARIMA fit with a four-position seasonal cycle.
    synthetic = np.zeros(400)
    noise = rng.normal(size=400)
    for i in range(4, 400):
        synthetic[i] = .4 * synthetic[i-1] + .2 * synthetic[i-4] + noise[i]
    fit = SARIMAX(synthetic, order=(1, 0, 0), seasonal_order=(1, 0, 0, 4),
                  trend='n', loglikelihood_burn=5).fit(disp=False, maxiter=300)
    residuals = np.asarray(fit.resid)[5:]
    centered = residuals - residuals.mean()
    n, lag, model_df = len(centered), 12, 2
    denominator = np.dot(centered, centered)
    correlations = np.array([np.dot(centered[k:], centered[:-k]) / denominator
                             for k in range(1, lag + 1)])
    statistic = float(n * (n + 2) * np.sum(correlations**2 / (n - np.arange(1, lag + 1))))
    unadjusted = acorr_ljungbox(residuals, lags=[lag], return_df=True)
    adjusted = acorr_ljungbox(residuals, lags=[lag], model_df=model_df, return_df=True)
    expected_aic = float(-2 * fit.llf + 2 * fit.df_model)
    expected_adjusted_p = float(chi2.sf(statistic, lag - model_df))
    assert np.isclose(expected_aic, fit.aic)
    assert np.isclose(statistic, adjusted.lb_stat.iloc[0])
    assert np.isclose(expected_adjusted_p, adjusted.lb_pvalue.iloc[0])
    assert burn_checks[0]['loglikelihood_burn'] != burn_checks[1]['loglikelihood_burn']
    output = {
        'statsmodels_version': statsmodels.__version__,
        'offline_same_d_D_burn_comparison': burn_checks,
        'synthetic_sarima': {
            'order': [1, 0, 0], 'seasonal_order': [1, 0, 0, 4],
            'converged': bool(fit.mle_retvals['converged']),
            'log_likelihood': float(fit.llf), 'df_model': float(fit.df_model),
            'library_aic': float(fit.aic), 'independent_aic': expected_aic,
            'residual_n': n, 'ljung_box_lag': lag, 'model_df': model_df,
            'independent_Q': statistic, 'library_Q': float(adjusted.lb_stat.iloc[0]),
            'unadjusted_p_current_weekly_call': float(unadjusted.lb_pvalue.iloc[0]),
            'adjusted_library_p': float(adjusted.lb_pvalue.iloc[0]),
            'independent_adjusted_p': expected_adjusted_p,
        },
        'limitations': 'Synthetic arithmetic checks do not validate real-data forecasts. '
                        'Seasonal-52 comparison constructs models only, with fixed d=0 and D=1.',
    }
    target = Path(__file__).with_name('sarima_diagnostic_checks.json')
    target.write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
