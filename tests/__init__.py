def load_confirmed_data(*args, **kwargs):
    """Legacy ingestion contracts exercise parsing plus explicit confirmation."""
    from dashboard.callbacks.data_callbacks import load_data, confirm_pending_upload
    result = load_data(*args, **kwargs)
    summary = result[2]
    if isinstance(summary, dict) and summary.get("pending_confirmation"):
        return confirm_pending_upload(summary, confirmed=True)
    return result
