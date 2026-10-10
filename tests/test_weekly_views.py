"""Forecast presentation and calendar-aware historical controls."""
from dashboard.weekly import ui
from dashboard.weekly.charts import forecast_chart
from dashboard.weekly.outputs import historical_summary
from tests.test_weekly import dataset, row


def test_philippine_timestamp_display_preserves_source_dates():
    from dashboard.weekly.presentation import display_timestamp

    assert display_timestamp('2026-10-09T01:10:51.717416+00:00') == 'Oct 9, 2026, 9:10 AM PHT'
    assert display_timestamp('2026-10-09T20:10:00Z') == 'Oct 10, 2026, 4:10 AM PHT'
    assert display_timestamp('2026-10-09T09:10:00+08:00') == 'Oct 9, 2026, 9:10 AM PHT'
    assert display_timestamp('2026-10-09') == 'Oct 9, 2026'
    assert display_timestamp(None) == 'Not specified'
    assert display_timestamp('2026-10-09T09:10:00').endswith('(timezone not specified)')
    assert display_timestamp('Unknown source date') == 'Unknown source date'


def test_data_page_omits_study_eligibility_that_describes_no_property_of_the_file():
    """The eligibility reasons are governance state, identical for any upload.

    Rendering them beside a page that describes one specific workbook made them
    read as defects in that workbook, so they come off the Data page. They must
    survive on Overview, or the last visible copy of that status is gone.
    """
    from dashboard.weekly.presentation import friendly_reason

    active = dataset()
    active['eligible'] = False
    active['eligibility_reasons'] = [
        'The weekly study protocol and its required history still need documented approval.'
    ]
    reason = friendly_reason(active['eligibility_reasons'][0])

    data_page = str(ui.render('Data', active, 'Measles', None, 13, 'Weekly')[0])
    assert reason not in data_page

    overview = str(ui.render('Overview', active, 'Measles', None, 13, 'Weekly')[0])
    assert reason in overview


def test_data_navigation_response_stays_compact_and_preserves_records():
    import json
    from plotly.utils import PlotlyJSONEncoder

    active = dataset([row(w, 0, year=y) for y in range(2015, 2026) for w in range(1, 53)],
                     reporting_status='unknown')
    output = ui.render('Data', active, 'Measles', None, 13, 'Weekly')
    payload = json.dumps(output, cls=PlotlyJSONEncoder)
    assert len(payload.encode()) < 100_000
    assert output[-1] == []
    assert 'Showing the first 20 of 572 findings' in payload
    assert '"page_size": 10' in payload
    assert len(active['records']) == 572
    about = ui.render('About the Model', active, 'Measles', None, 13, 'Weekly')
    assert 'Source information and eligibility evidence' in str(about[-1])


def test_other_modules_do_not_build_hidden_diagnostics(monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError('Hidden diagnostics should not be built during navigation')

    monkeypatch.setattr(ui, 'advanced', unexpected)
    for page in ('Overview', 'Historical Trends', 'Data', 'Forecast'):
        ui.render(page, dataset(), 'Measles', None, 13, 'Weekly')


def test_horizon_slices_both_models_without_changing_metrics():
    active = dataset()
    result = {'hybrid': list(range(52)), 'sarima': list(range(52)),
              'forecast_index': [{'year': None, 'horizon_week': i + 1} for i in range(52)],
              'metrics': {'hybrid': {'mae': 2, 'rmse': 20}}}
    for horizon in (4, 13, 26, 52):
        figure = forecast_chart(active, 'Measles', result, horizon)
        # Traces are identified by meta['model'], not by a substring of the
        # label. Matching on the label made the test depend on presentation
        # wording, which broke the moment the names were shortened for the
        # unified hover.
        predictions = [t for t in figure.data if (t.meta or {}).get('model')]
        assert len(predictions) == 2
        assert {t.meta['model'] for t in predictions} == {'hybrid', 'sarima'}
        assert all(len(t.y) == horizon for t in predictions)
        assert str(horizon) in figure.layout.title.text
    assert result['metrics']['hybrid']['mae'] == 2


def test_every_chart_trace_declares_hover_text_and_short_names():
    """A trace without hovertemplate prints raw float precision on hover.

    Forecast values are expected counts, so Plotly's default rendered values
    like 33.55735 - six significant figures for a quantity measured in whole
    people. Long names were also being ellipsised by the unified hover, and the
    invisible lower bound of the uncertainty band surfaced as an unnamed row.
    """
    active = dataset()
    result = {'hybrid': [10.5] * 52, 'sarima': [9.25] * 52,
              'forecast_index': [{'year': None, 'horizon_week': i + 1} for i in range(52)],
              'range': {'lower': [1.5] * 52, 'upper': [30.125] * 52}}
    figure = forecast_chart(active, 'Measles', result, 52)

    for trace in figure.data:
        if trace.hoverinfo == 'skip':
            continue  # deliberately absent from the hover, not merely unformatted
        assert trace.hovertemplate, f'trace {trace.name!r} would print raw float precision'

    labels = [t.name for t in figure.data if t.showlegend is not False]
    assert labels, 'expected legend entries'
    assert all(len(name) <= 14 for name in labels), labels
    assert all('...' not in name and '…' not in name for name in labels), labels

    # The band helper must stay in the figure to produce the fill, but must not
    # appear in the hover as a bare number.
    helper = [t for t in figure.data if t.showlegend is False]
    assert helper, 'the fill helper trace should still exist'
    assert all(t.hoverinfo == 'skip' for t in helper)

    reported = next(t for t in figure.data if t.name == 'Reported')
    assert reported.hovertemplate == '%{y:,.0f}', 'reported counts are whole people'
    forecast = next(t for t in figure.data if (t.meta or {}).get('model') == 'hybrid')
    assert forecast.hovertemplate == '%{y:,.1f}', 'forecast values keep one decimal'


def test_excluded_reports_not_duplicated_in_complete_trace():
    active = dataset(reporting_status='unknown')
    figure = forecast_chart(active, 'Measles', None, 4)
    assert all(value is None for value in figure.data[0].y)
    assert list(figure.data[1].y) == [r['case_count'] for r in active['records']]


def test_month_quarter_options_and_aggregation():
    active = dataset([row(1, 2, week_start_date='2025-01-06'), row(6, 3, week_start_date='2025-02-10'),
                      row(15, 4, week_start_date='2025-04-07')])
    assert ui.history_options(active, 'Measles', 'Monthly')[0] == ['2025-01', '2025-02', '2025-04']
    assert ui.history_options(active, 'Measles', 'Quarterly')[0] == ['2025Q1', '2025Q2']
    assert historical_summary(active, 'Measles', 'Quarterly')[1] == [5, 4]
    assert not ui.history_availability(active, 'Measles')[0][1]['disabled']
    content = str(ui.render('Historical Trends', active, 'Measles', None, 4, 'Monthly', '2025-02', '2025-04')[0])
    assert '2025-02' in content and 'Monthly summary' in content


def test_missing_dates_disable_calendar_views_and_reset_selection():
    options, message, selected = ui.history_availability(dataset(), 'Measles', 'Quarterly')
    assert selected == 'Weekly' and options[1]['disabled'] and options[2]['disabled']
    assert 'Week Start Date' in message


def test_overview_uses_new_dataset_when_disease_selection_is_stale():
    active = dataset([{'disease': 'Dengue', 'year': 2025, 'morbidity_week': 12, 'case_count': 7}], reporting_status='unknown')
    content = str(ui.render('Overview', active, 'Measles', None, 4, 'Weekly')[0])
    assert 'Dengue' in content and 'Latest Supplied Week' in content and 'Week 12' in content


def test_metrics_show_values_and_explain_unavailability():
    result = {'metrics': {'hybrid': {'mae': 1.25, 'rmse': 12.5}, 'sarima': {'mae': 2.5, 'rmse': 25}},
              'evaluation': {'status': 'Retrospective evaluation', 'hybrid_status': 'Available', 'sarima_status': 'Available'}}
    text = str(ui.metrics_table(result))
    assert all(value in text for value in ['1.25', '12.5', '2.5', '25', 'MAE', 'RMSE'])
    assert 'protocol pending' in str(ui.metrics_table({'evaluation': {'status': 'protocol pending'}}))
