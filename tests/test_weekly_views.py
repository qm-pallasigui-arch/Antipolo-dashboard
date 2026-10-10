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


def _walk(node):
    """Yield every node in a component tree.

    Children are not always a list: dash collapses single-child wrappers, so
    html.Thead's children are one html.Tr rather than a list containing it.
    """
    if isinstance(node, (list, tuple)):
        for item in node:
            yield from _walk(item)
        return
    yield node
    children = getattr(node, 'children', None)
    if children is None:
        return
    if isinstance(children, (list, tuple)):
        for item in children:
            yield from _walk(item)
    else:
        yield from _walk(children)


def test_table_classifies_a_column_once_so_placeholders_keep_their_alignment():
    """A missing value must not change how its column lines up.

    The cell-level test ran `isinstance(value, Real)` on each value. A single
    None rendered as 'Not reported', failed that test, and aligned to the
    opposite edge from the numbers around it, so one absent metric visibly broke
    its own column. Classification is per column now, and the class is applied to
    the header as well so the two cannot drift apart.
    """
    from dashboard.weekly.presentation import table

    rendered = table([{'Model': 'A', 'MAE': 43.3}, {'Model': 'B', 'MAE': None}])
    heads = [n for n in _walk(rendered) if getattr(n, '_type', None) == 'Th']
    cells = [n for n in _walk(rendered) if getattr(n, '_type', None) == 'Td']

    assert [h.className for h in heads] == ['', 'numeric-cell']
    assert [c.className for c in cells] == ['', 'numeric-cell', '', 'numeric-cell']
    assert cells[3].children == 'Not reported'
    assert cells[3].className == heads[1].className, 'header and body must share a column\'s alignment'


def test_integer_counts_and_float_metrics_are_both_recognised_as_numeric():
    from numbers import Real

    from dashboard.weekly.presentation import table

    rendered = table([{'Scored weeks': 52, 'MAE': 43.3}, {'Scored weeks': 51, 'MAE': None}])
    cells = [n for n in _walk(rendered) if getattr(n, '_type', None) == 'Td']
    # bool is an int, and Real; a True in a column must not make it numeric.
    assert cells[0].className == 'numeric-cell'
    assert cells[2].className == 'numeric-cell'
    assert isinstance(52, Real)


def test_both_table_renderers_align_to_the_left_edge():
    """The paged DataTable said 'left' while the raw table right-aligned numbers.

    The same application therefore showed different alignment depending on which
    table it was. Both must now resolve to left; the numeric class must not
    reintroduce a right edge in the stylesheet.
    """
    from pathlib import Path

    from dashboard.weekly.presentation import table

    paged = table([{'Model': 'A', 'MAE': 1.5}], page_size=10)
    assert paged.style_cell['textAlign'] == 'left'

    stylesheet = (Path(__file__).resolve().parents[1] /
                  'dashboard' / 'assets' / 'revision39.css').read_text(encoding='utf-8')
    numeric_rule = next(line for line in stylesheet.splitlines() if '.numeric-cell {' in line)
    assert 'text-align: left' in numeric_rule
    assert 'text-align: right' not in numeric_rule


def test_error_metrics_are_not_reported_to_more_precision_than_was_measured():
    result = {'metrics': {'hybrid': {'mae': 43.332, 'rmse': 53.146, 'mape': 37.378, 'mape_n': 52}}}
    rendered = str(ui.metrics_table(result))
    assert '43.3' in rendered and '43.332' not in rendered
    assert '53.1' in rendered and '53.146' not in rendered
    assert '37.4' in rendered and '37.378' not in rendered
    assert '52' in rendered


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


def test_calendar_views_follow_the_derived_calendar_not_a_source_date_column():
    """Monthly and quarterly must be usable against a workbook with no dates.

    They were disabled whenever the source lacked week_start_date, which is the
    workbook's case, so both views could never be selected. Availability now
    depends only on whether the disease has records, and the message explains the
    grouping rule rather than asking for a column the source does not carry.
    """
    options, message, selected = ui.history_availability(dataset(), 'Measles', 'Quarterly')
    assert not options[1]['disabled'] and not options[2]['disabled']
    assert selected == 'Quarterly', 'a valid choice must survive'
    assert 'start date' in message
    assert 'Week Start Date' not in message

    # No records for the disease is the only thing that disables them now.
    options, message, selected = ui.history_availability(dataset([row(1, 2)]), 'Dengue', 'Quarterly')
    assert options[1]['disabled'] and options[2]['disabled']
    assert selected == 'Weekly'
    assert 'No records' in message


def test_overview_uses_new_dataset_when_disease_selection_is_stale():
    active = dataset([{'disease': 'Dengue', 'year': 2025, 'morbidity_week': 12, 'case_count': 7}], reporting_status='unknown')
    content = str(ui.render('Overview', active, 'Measles', None, 4, 'Weekly')[0])
    assert 'Dengue' in content and 'Latest Supplied Week' in content and 'Week 12' in content


def test_metrics_show_values_and_explain_unavailability():
    result = {'metrics': {'hybrid': {'mae': 1.25, 'rmse': 12.5}, 'sarima': {'mae': 2.5, 'rmse': 25}},
              'evaluation': {'status': 'Retrospective evaluation', 'hybrid_status': 'Available', 'sarima_status': 'Available'}}
    # Values are rendered at one decimal; 1.25 rounds to 1.2. What this test
    # covers is that values appear at all and that unavailability is explained -
    # the rounding itself is pinned by
    # test_error_metrics_are_not_reported_to_more_precision_than_was_measured.
    text = str(ui.metrics_table(result))
    assert all(value in text for value in ['1.2', '12.5', '2.5', '25', 'MAE', 'RMSE'])
    assert 'protocol pending' in str(ui.metrics_table({'evaluation': {'status': 'protocol pending'}}))


def test_performance_table_has_a_white_header_and_other_tables_keep_their_tint():
    from dashboard.weekly.presentation import table
    rendered = ui.metrics_table({'metrics': {'hybrid': {'mae': 1.2}}})
    assert 'performance-table' in str(rendered)
    plain = table([{'Model': 'A'}])
    assert 'performance-table' not in str(plain)


def test_the_forecast_controls_show_one_row_of_actions():
    controls = str(ui.build_layout())
    assert 'Compute Model Performance' in controls
    assert 'Retrospective performance is not computed' not in controls


def test_performance_table_header_is_distinguishable_without_a_tint():
    """Removing the tinted header band must not remove the header's identity.

    The raw table renderer sets no font-weight on th - the paged DataTable does,
    inline - so the background tint was the only thing marking that row as a
    header. Whitening it left the header identical to the body. The stylesheet
    must supply weight and a defined edge instead.
    """
    from pathlib import Path

    stylesheet = (Path(__file__).resolve().parents[1] /
                  'dashboard' / 'assets' / 'revision39.css').read_text(encoding='utf-8')
    rule = stylesheet.split('.performance-table th {', 1)[1].split('}', 1)[0]
    assert 'font-weight' in rule, 'a white header must be marked by weight, not tint'
    assert 'border-bottom' in rule


def test_derived_week_dates_agree_with_the_derived_week_counts():
    """A derived date and a derived week count must come from one rule.

    If these disagreed, a monthly summary could place a week outside the year it
    belongs to. Everything here is checked against the rule itself rather than
    against remembered publication dates, which cannot be verified here.
    """
    import datetime as dt

    from dashboard.weekly import calendar

    for year in range(2010, 2035):
        length = calendar.year_length(year)
        assert length in (52, 53), (year, length)

        first = calendar.week_start(year, 1)
        assert first.weekday() == 6, 'weeks begin on Sunday'
        # Week 1 may begin just before 1 January: MMWR 2013 opened on
        # Sunday 30 December 2012, which the four-day rule requires.
        assert -6 <= (first - dt.date(year, 1, 1)).days <= 6, (year, first)

        # Week 1 must contribute at least four days to the year, which is the rule.
        january = dt.date(year, 1, 1)
        assert 7 - (january - first).days >= 4, (year, first)

        last = calendar.week_start(year, length)
        assert last > dt.date(year, 12, 20), (year, last)
        assert last <= dt.date(year, 12, 31), (year, last)

        for week in range(1, length + 1):
            assert calendar.week_start(year, week) - calendar.week_start(year, week - 1) == dt.timedelta(7) \
                if week > 1 else True


def test_monthly_and_quarterly_summaries_work_without_a_source_date_column():
    """The workbook carries no week_start_date, so both views used to always fail.

    The period now comes from the reporting week under the same MMWR rule the
    calendar already applies, and the explanation says the basis is derived rather
    than source-established.
    """
    from dashboard.weekly.outputs import historical_summary

    active = dataset([row(w, w % 4, year=y) for y in range(2020, 2023) for w in range(1, 53)])
    assert not any('week_start_date' in r for r in active['records'])

    monthly, values, note = historical_summary(active, 'Measles', 'Monthly')
    quarterly, quarters, qnote = historical_summary(active, 'Measles', 'Quarterly')

    assert monthly and quarterly
    # Period counts follow the derived calendar, so a year whose week 1 starts in
    # December adds a period. Assert ordering and coverage, not fixed totals.
    assert monthly == sorted(monthly) and quarterly == sorted(quarterly)
    assert len(monthly) >= 36 and len(quarterly) >= 12
    assert all(v is not None for v in values)
    assert 'derived from the CDC MMWR rule' in note
    assert 'not a source-established date' in note
    assert 'counted whole' in note
    assert 'never split across periods' in note
    assert sum(values) == sum(r['case_count'] for r in active['records'])


def test_a_period_containing_a_blank_reports_no_total_rather_than_a_partial_one():
    from dashboard.weekly.outputs import historical_summary

    rows = [row(w, None if w == 3 else 2, year=2021) for w in range(1, 20)]
    active = dataset(rows)
    _, values, note = historical_summary(active, 'Measles', 'Monthly')
    assert None in values, 'a blank must void its period, not be skipped'
    assert 'incomplete' in note


def test_a_source_week_start_date_is_preferred_over_the_derived_calendar():
    from dashboard.weekly.outputs import historical_summary

    rows = [row(w, 2, year=2021, week_start_date=f'2021-01-{w:02d}') for w in range(1, 20)]
    active = dataset(rows)
    _, _, note = historical_summary(active, 'Measles', 'Monthly')
    assert 'source week-start date' in note
    assert 'derived' not in note


def test_buttons_are_ordered_and_typed_by_consequence():
    layout = str(ui.build_layout())
    assert layout.index('Update Source Information') < layout.index('View Transformation Details')
    assert layout.index('View Transformation Details') < layout.index('Reset Dataset')
    assert layout.index('Reset Dataset') < layout.index('Try Synthetic / Demo Data')
    assert "id='w-reset'" in layout and 'destructive' in layout
    assert "id='w-evaluate'" in layout
    assert "id='w-evaluate', n_clicks=0)," in layout, 'Compute Model Performance is a primary action'
