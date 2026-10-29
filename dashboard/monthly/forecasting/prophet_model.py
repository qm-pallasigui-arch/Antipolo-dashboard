"""Prophet fitting on actual calendar dates; parameters supplied by approved methodology."""
import pandas as pd
import numpy as np
from .adapter import observed_frame
from .errors import ForecastComponentError


def generate_prophet_base(frame, dates, config):
    """Fit only observed real dates and predict only requested real calendar months."""
    try:
        from prophet import Prophet
        from threadpoolctl import threadpool_limits
        observed = observed_frame(frame)
        history = observed[['actual_timestamp', 'consultation_count']].rename(columns={'actual_timestamp': 'ds', 'consultation_count': 'y'})
        with threadpool_limits(limits=config.threads):
            model = Prophet(**config.prophet)
            model.fit(history, seed=config.seed)
            fitted = model.predict(history[['ds']])['yhat'].to_numpy(dtype=float)
            forecast = model.predict(pd.DataFrame({'ds': pd.to_datetime(dates)}))['yhat'].to_numpy(dtype=float)
        if not np.isfinite(fitted).all() or not np.isfinite(forecast).all():
            raise ValueError('Nonfinite Prophet output.')
        return pd.Series(fitted, index=observed.actual_timestamp), forecast
    except Exception as exc:
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
