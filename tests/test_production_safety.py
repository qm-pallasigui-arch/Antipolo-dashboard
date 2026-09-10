"""Regression tests for public upload and production-facing error behavior."""

import base64

from dashboard.callbacks.data_callbacks import load_data
from dashboard.config import MAX_UPLOAD_BYTES
import app as app_entry


def _upload(payload: bytes, filename: str):
    contents = "data:application/octet-stream;base64," + base64.b64encode(payload).decode("ascii")
    return load_data(contents, filename, None)


def test_oversized_upload_is_rejected_before_parsing():
    _, status = _upload(b"x" * (MAX_UPLOAD_BYTES + 1), "large.csv")
    assert "exceeds" in status.lower()
    assert "traceback" not in status.lower()


def test_corrupt_xlsx_has_a_bounded_user_message():
    _, status = _upload(b"not an xlsx", "broken.xlsx")
    assert "could not open" in status.lower()
    assert "badzipfile" not in status.lower()


def test_legacy_xls_is_not_advertised_or_accepted():
    _, status = _upload(b"not an xls", "legacy.xls")
    assert "unsupported file type" in status.lower()


def test_health_endpoint_is_lightweight_and_successful():
    response = app_entry.server.test_client().get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}