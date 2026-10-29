"""Compatibility entrypoint for the monthly forecast service."""
from .forecasting.config import METHOD_PENDING, MethodologyPending
from .services.forecast_service import ForecastService, ModelFailure, NotEligible

__all__ = ['METHOD_PENDING', 'MethodologyPending', 'ForecastService', 'ModelFailure', 'NotEligible']
