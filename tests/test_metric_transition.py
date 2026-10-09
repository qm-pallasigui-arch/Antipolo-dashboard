"""Operational metric schema and historical-result compatibility."""
import copy
import json
from types import SimpleNamespace

import pytest

from dashboard.modeling.historical_metrics import compute_metrics as historical_metrics
from dashboard.weekly import model, outputs, ui
from dashboard.weekly.result_schema import current_result
from tests.test_weekly import dataset, protocol


@pytest.mark.parametrize('actual,predicted', [([0, 0], [0, 1]), ([0, 2], [1, 2]), ([3, 7, 1], [2, 4, 8])])
def test_remaining_metrics_exactly_match_historical(actual, predicted):
    old = historical_metrics(actual, predicted)
    old.pop('wape')
    assert model.compute_metrics(actual, predicted) == old


def test_real_forecasts_unchanged_with_new_scoring(monkeypatch):
    d, c = dataset(), protocol()
    d['records'][-4]['case_count'] = None
    new = model.run(d, 'Measles', c)
    monkeypatch.setattr(model, 'compute_metrics', historical_metrics)
    old = model.run(d, 'Measles', c)
    assert new['hybrid'] is not None and new['sarima'] is not None
    assert new['evaluation']['excluded_missing_actuals'] == 1
    old = current_result(old)
    for result in (old, new):
        result.pop('issued_at')
    assert old == new


def test_old_results_filtered_at_every_boundary(tmp_path, monkeypatch):
    d = dataset()
    result = model.run(d, 'Measles', protocol())
    assert result['hybrid'] is not None
    for group in [result['metrics'], *[h['metrics'] for h in result['horizon_metrics'].values()]]:
        for metric in group.values():
            if metric:
                metric['wape'] = 99
    original = copy.deepcopy(result)
    assert 'wape' not in str(ui.advanced(result)).lower()
    assert 'wape' not in str(ui.metrics_table(result)).lower()
    assert 'wape' not in str(ui.horizon_metrics_table(result)).lower()
    assert 'wape' not in outputs.export_frame(d, result).to_csv().lower()
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id='w-export-json'))
    downloaded = json.loads(ui.export(0, 1, d, result)['content'])
    assert 'wape' not in json.dumps(downloaded).lower()
    assert downloaded['dataset'] == d
    identifier = outputs.save_snapshot(d, result, tmp_path)
    assert 'wape' not in (tmp_path / f'{identifier}.json').read_text().lower()
    monkeypatch.setattr(ui, 'ctx', SimpleNamespace(triggered_id='w-run'))
    monkeypatch.setattr(ui, 'model_configuration', protocol)
    monkeypatch.setattr(ui.jobs, 'submit', lambda *args: pytest.fail('Cache must be reused'))
    assert ui.forecast(1, d, 'Measles', prior=result) == current_result(result)
    assert result == original
