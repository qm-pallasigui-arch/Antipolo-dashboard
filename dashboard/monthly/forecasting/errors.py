"""Explicit component failure statuses; no automatic algorithm substitution."""


class ForecastComponentError(RuntimeError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
