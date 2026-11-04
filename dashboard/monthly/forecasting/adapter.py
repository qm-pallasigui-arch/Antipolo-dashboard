"""Canonical-to-model boundary; retain actual timestamps and source states."""
import pandas as pd
from .errors import ForecastComponentError


def modeling_frame(rows):
    frame = pd.DataFrame(rows).copy(deep=True)
    if frame.empty:
        raise ForecastComponentError('xgboost_insufficient_history', 'No monthly observations supplied to the model workflow.')
    frame['actual_timestamp'] = pd.to_datetime(dict(year=frame.year, month=frame.month_number, day=1))
    if frame.actual_timestamp.duplicated().any():
        raise ValueError('Model input must contain unique calendar months for one block.')
    if frame.icd10_block.nunique() != 1:
        raise ValueError('Model input must contain exactly one ICD-10 block.')
    return frame.sort_values('actual_timestamp').reset_index(drop=True)


def observed_frame(frame):
    return frame.loc[frame.observation_status.isin(('observed', 'observed_zero')) & frame.consultation_count.notna()].copy()
