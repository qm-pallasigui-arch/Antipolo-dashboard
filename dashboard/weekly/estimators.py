"""Shared estimators for offline selection, held-out testing and deployment.

SARIMAX is the statsmodels implementation of SARIMA when exog is absent.
All candidates use levels (no simple differencing), approximate diffuse
initialization with variance 1e6, and a common 108-position likelihood burn.
108 exceeds the largest state dimension (108) of the declared 144-model grid.
Missing observations contribute no likelihood but retain their positions.
"""
import warnings

import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller

COMMON_BURN = 108
SEEDS = (42, 137, 2026)
VERSION = 'weekly-3'


def adf_diagnostic(values):
    values = np.asarray(values, float)
    result = {'status': 'unavailable', 'statistic': None, 'pvalue': None,
              'selected_lags': None, 'observations': None,
              'role': 'Stationarity diagnostic; AIC selects ADF regression lags, not SARIMA orders.'}
    if not np.isfinite(values).all() or len(values) < 8 or np.ptp(values) == 0:
        result['reason'] = 'Gapped, constant or insufficient series; no positions compressed.'
        return result
    try:
        stat, p, lag, n, *_ = adfuller(values, autolag='AIC')
        result.update(status='available', statistic=float(stat), pvalue=float(p),
                      selected_lags=int(lag), observations=int(n), adf_pvalue=float(p))
    except ValueError:
        result['reason'] = 'ADF could not be estimated.'
    return result


def ljung_box(residuals, candidate):
    p, _, q = candidate['order']
    P, _, Q, _ = candidate['seasonal_order']
    df = p + q + P + Q
    values = np.asarray(residuals, float)
    rows = []
    for lag in (13, 26, 52):
        row = {'lag': lag, 'model_df': df, 'observations': int(np.isfinite(values).sum()),
               'statistic': None, 'pvalue': None, 'status': 'unavailable'}
        # Do not turn gaps into neighboring observations. Require at least 2*lag.
        if lag > df and len(values) >= 2 * lag and np.isfinite(values).all() and np.ptp(values) > 0:
            lb = acorr_ljungbox(values, lags=[lag], model_df=df, return_df=True)
            if np.isfinite(lb.iloc[0]).all():
                row.update(status='available', statistic=float(lb.lb_stat.iloc[0]),
                           pvalue=float(lb.lb_pvalue.iloc[0]))
        if row['status'] == 'unavailable':
            row['reason'] = 'Gaps, constant residuals, insufficient observations or lag <= model_df.'
        rows.append(row)
    return rows


def fit_sarima(values, steps, candidate, config):
    values = np.asarray(values, float)
    burn = config['residual_burn']
    if np.isfinite(values).sum() < config['minimum_training_weeks'] or len(values) <= burn:
        raise ValueError('Insufficient historical observations for SARIMA fitting.')
    if np.isinf(values).any() or (config['missing_policy'] == 'reject' and np.isnan(values).any()):
        raise ValueError('Invalid observations or rejected missing positions.')
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        model = SARIMAX(values, order=candidate['order'], seasonal_order=candidate['seasonal_order'],
                        trend=candidate.get('trend', 'n'), enforce_stationarity=True,
                        enforce_invertibility=True, simple_differencing=False,
                        initialization='approximate_diffuse', initial_variance=1e6,
                        loglikelihood_burn=burn, missing='none')
        fit = model.fit(method='lbfgs', maxiter=config['maxiter'], disp=False)
    if not fit.mle_retvals.get('converged', False):
        raise ValueError('SARIMA optimizer did not converge.')
    if not np.isfinite(fit.params).all() or not np.isfinite(fit.aic) or not np.isfinite(fit.llf):
        raise ValueError('SARIMA parameters or likelihood are nonfinite.')
    prediction = np.asarray(fit.forecast(steps), float)
    if prediction.shape != (steps,) or not np.isfinite(prediction).all():
        raise ValueError('Nonfinite SARIMA forecast.')
    residuals = values - np.asarray(fit.fittedvalues)
    residuals[:burn] = np.nan
    record = {**candidate, 'status': 'available', 'fit_status': 'available', 'converged': True,
              'aic': float(fit.aic), 'log_likelihood': float(fit.llf),
              'parameter_count': int(fit.df_model), 'likelihood_burn': int(fit.loglikelihood_burn),
              'effective_observation_count': int(np.isfinite(values[burn:]).sum()),
              'effective_positions': len(values) - burn,
              'warnings': [str(w.message) for w in caught],
              'fitted_parameters': dict(zip(fit.param_names, map(float, fit.params))),
              'ljung_box': ljung_box(residuals[burn:], candidate)}
    return prediction, residuals, record


def nnar_samples(residuals, lags):
    X, y = [], []
    for i in range(max(lags), len(residuals)):
        window = [residuals[i - lag] for lag in lags]
        if np.isfinite(window).all() and np.isfinite(residuals[i]):
            X.append(window)
            y.append(residuals[i])
    return np.asarray(X), np.asarray(y)


def nnar(residuals, steps, c, progress=None):
    lags = c['nnar_lags']
    X, y = nnar_samples(residuals, lags)
    if len(y) < c['minimum_residual_examples']:
        raise ValueError('Insufficient complete residual lag windows; no imputation was performed.')
    if not np.isfinite(residuals[-max(lags):]).all():
        raise ValueError('Terminal residual lag window contains missing observations.')
    scaler = StandardScaler().fit(X)
    network = MLPRegressor(hidden_layer_sizes=(c['hidden_nodes'],), activation='relu', solver='lbfgs',
                           max_iter=c['nnar_maxiter'], alpha=c['alpha'], random_state=c['seed'])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        network.fit(scaler.transform(X), y)
    if any('converg' in str(w.message).lower() for w in caught):
        raise ValueError('NNAR optimizer did not converge.')
    if progress:
        progress('residual_forecast', 'NNAR fit completed. Generating recursive residual forecasts.')
    history, predicted = list(residuals), []
    for _ in range(steps):
        value = float(network.predict(scaler.transform([[history[-lag] for lag in lags]]))[0])
        if not np.isfinite(value):
            raise ValueError('NNAR generated a nonfinite value.')
        predicted.append(value)
        history.append(value)
    return np.asarray(predicted), [str(w.message) for w in caught]
