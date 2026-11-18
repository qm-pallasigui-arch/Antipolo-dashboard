"""Prophet fitting on actual calendar dates; parameters supplied by approved methodology."""
import pandas as pd
import numpy as np
import logging
from pathlib import Path
import secrets
from .adapter import observed_frame
from .errors import ForecastComponentError


def check_model_workspace(directory):
    """Use one direct write: Windows tempfile retries can conceal denied access."""
    probe = Path(directory) / ('antipolo-probe-' + secrets.token_hex(12))
    try:
        with probe.open('x') as output:
            output.write('workspace check')
    except OSError as exc:
        raise ForecastComponentError('prophet_failed',
            'Model temporary folder is not writable. Restart the server with writable temporary storage, then retry.') from exc
    finally:
        if probe.exists():
            probe.unlink()


def generate_prophet_base(frame, dates, config):
    """Fit only observed real dates and predict only requested real calendar months."""
    try:
        from prophet import Prophet
        import cmdstanpy
        from threadpoolctl import threadpool_limits
        check_model_workspace(cmdstanpy._TMPDIR)
        observed = observed_frame(frame)
        history = observed[['actual_timestamp', 'consultation_count']].rename(columns={'actual_timestamp': 'ds', 'consultation_count': 'y'})
        with threadpool_limits(limits=config.threads):
            model = Prophet(**config.prophet)
            model.fit(history, seed=config.seed, timeout=180)
            fitted = model.predict(history[['ds']])['yhat'].to_numpy(dtype=float)
            forecast = model.predict(pd.DataFrame({'ds': pd.to_datetime(dates)}))['yhat'].to_numpy(dtype=float)
        if not np.isfinite(fitted).all() or not np.isfinite(forecast).all():
            raise ValueError('Nonfinite Prophet output.')
        return pd.Series(fitted, index=observed.actual_timestamp), forecast
    except ForecastComponentError:
        raise
    except Exception as exc:
        logging.getLogger(__name__).exception('Prophet fitting or prediction failed')
        raise ForecastComponentError('prophet_failed', 'Prophet fitting or prediction failed; no substitute forecast was generated.') from exc


def fit_predict(observations, dates, parameters, *, fit_parameters, threads):
    from prophet import Prophet
    from threadpoolctl import threadpool_limits
    if isinstance(threads, bool) or not isinstance(threads, int) or threads < 1:
        raise ValueError('An explicit positive CPU thread limit is required.')
    if 'seed' not in fit_parameters:
        raise ValueError('An explicit fitting seed is required.')
    rows = [r for r in observations if r['observation_status'] in ('observed', 'observed_zero')]
    history = pd.DataFrame({'ds': [pd.Timestamp(r['year'], r['month_number'], 1) for r in rows],
                            'y': [r['consultation_count'] for r in rows]}).sort_values('ds')
    if history.empty or history.ds.duplicated().any():
        raise ValueError('Prophet requires unique observed monthly dates.')
    model = Prophet(**parameters)
    with threadpool_limits(limits=threads):
        model.fit(history, **fit_parameters)
    return model.predict(pd.DataFrame({'ds': dates}))['yhat'].tolist()
