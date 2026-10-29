# LEGACY RESEARCH CODE
# Not part of the finalized Prophet-XGBoost thesis implementation.
# Retained only for historical/reproducibility purposes.
"""Prototype forecasting inference. Developer CLI only; dashboard uses the eligibility-gated service."""
from dashboard.monthly.forecasting.icd_inference import forecast_block, forecast_series, main

__all__ = ['forecast_block', 'forecast_series', 'main']

if __name__ == '__main__':
    main()
