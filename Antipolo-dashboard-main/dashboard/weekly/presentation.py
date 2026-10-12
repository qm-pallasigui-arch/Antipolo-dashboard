"""Plain-language summaries shared by review and active-data views."""
from dash import dash_table, html
from numbers import Real
from datetime import date, datetime, timedelta, timezone


def display_timestamp(value, missing='Not specified'):
    """Readable Philippine time; preserve date-only and unzoned source facts."""
    if not value:
        return missing
    text = str(value).strip()
    try:
        if len(text) == 10:
            parsed_date = date.fromisoformat(text)
            return f'{parsed_date:%b} {parsed_date.day}, {parsed_date.year}'
        parsed = datetime.fromisoformat(text.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            return text + ' (timezone not specified)'
        local = parsed.astimezone(timezone(timedelta(hours=8)))
        return f'{local:%b} {local.day}, {local.year}, {local.hour % 12 or 12}:{local:%M %p} PHT'
    except ValueError:
        return text


def source_freshness(metadata, missing='Not specified'):
    return html.Div([
        html.H4('Source freshness'),
        html.Dl([html.Div([html.Dt(label), html.Dd(display_timestamp(metadata.get(key), missing))])
                 for label, key in [('Source date', 'source_date'), ('Uploaded', 'uploaded_at')]],
                className='freshness-details'),
    ], className='source-freshness')


def notice(text):
    return html.Div(text, className='message', role='status')


def disclosure(title, children):
    return html.Details([html.Summary(title), html.Div(children, className='disclosure-body')])


def table(rows, columns=None, limit=None, page_size=None, wrapper_class=''):
    if not rows:
        return html.P('None recorded.', className='muted')
    columns = columns or {key: key if key.isupper() else key.replace('_', ' ').title() for row in rows for key in row}
    shown = rows[:limit] if limit else rows
    # Classify a column once, from its rows, instead of testing each cell's
    # rendered value. The per-cell test classified on `str(value)`, so a single
    # missing value rendered as 'Not reported', failed the numeric test, and
    # aligned to the opposite edge from the numbers above and below it in its
    # own column. Deciding per column keeps a column internally consistent
    # whatever any individual cell holds.
    numeric = {key for key in columns
               if any(isinstance(row.get(key), Real) and not isinstance(row.get(key), bool)
                      for row in shown)}

    def cell_class(key):
        return 'numeric-cell' if key in numeric else ''

    def cell_text(row, key):
        value = row.get(key)
        return 'Not reported' if value is None or value == '' else str(value)

    if page_size:
        return dash_table.DataTable(
            data=[{key: cell_text(row, key) for key in columns} for row in shown],
            columns=[{'name': label, 'id': key} for key, label in columns.items()],
            page_action='native', page_size=page_size,
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '8px', 'fontFamily': 'inherit'},
            style_header={'fontWeight': 'bold', 'backgroundColor': '#edf7f6'},
        )
    return html.Div(html.Table([
        # The class goes on the header as well as the body, so a numeric column
        # is styled as one unit and the two renderers below cannot drift apart.
        html.Thead(html.Tr([html.Th(label, className=cell_class(key)) for key, label in columns.items()])),
        html.Tbody([html.Tr([html.Td(cell_text(row, key), className=cell_class(key)) for key in columns]) for row in shown]),
    ]), className=('table-scroll ' + wrapper_class).strip(), tabIndex=0)


def friendly_reason(reason):
    translations = {
        'No complete, reported weeks available for training.': 'No weeks are established as complete for training. Open Data → Update Source Information. If CESU/source documentation confirms the historical period is complete, select Historical reporting period complete and enter its evidence reference, then update the summary and confirm. Otherwise, obtain source confirmation; do not assume completeness from the age of the records.',
        'population:': 'The age group is not established as ages 5–19.',
        'case_classification:': 'Confirmed-only case status has not been established.',
        'location:': 'The source does not establish that these records cover Antipolo City.',
        'dataset_type:': 'The data have not been established as real surveillance records.',
        'frequency:': 'These records must represent weekly observations.',
        'Source metadata incomplete': 'Source information is incomplete. CESU/PIDSAR records and a source reference are required for thesis evaluation.',
        'Source metadata mismatch': 'The source information in some rows differs from the information supplied for the file.',
        'Row metadata': 'Some rows have missing or conflicting background information.',
        'Sufficient history': 'The weekly study protocol and its required history still need documented approval.',
        'Disease scope': 'The disease list still needs documented study approval.',
        'Formal evaluation': 'The effect of missing observations on thesis evaluation needs review.',
        'Week 53 statistical': 'The treatment of week 53 still needs study approval.',
        'Reporting-year calendar': 'The source reporting calendar needs to be confirmed.',
        'Duplicate observations': 'Some disease and week combinations appear more than once. Resolve these before using the data.',
        'Inconsistent disease': 'Some disease names differ only by spacing or letter case. Please check the source labels.',
    }
    return next((value for key, value in translations.items() if reason.startswith(key)), reason.replace('_', ' '))


def eligibility(dataset):
    if dataset['eligible']:
        label = 'Eligible for Thesis Evaluation'
    else:
        meta = dataset['metadata']
        known_mismatch = (meta.get('dataset_type') == 'synthetic'
                          or meta.get('population') not in (None, '', 'unknown', '5–19', '5-19')
                          or meta.get('case_classification') not in (None, '', 'unknown', 'confirmed'))
        label = 'Technical / Exploratory Only' if known_mismatch else 'Needs More Information'
    return disclosure(label, [html.P('This status indicates whether the dataset currently meets the study’s research-data requirements.'),
                              html.Ul([html.Li(friendly_reason(r)) for r in dataset['eligibility_reasons']])])


def quality_messages(dataset):
    q = dataset['quality']
    messages = []
    if q['missing_weeks']:
        messages.append('Some morbidity weeks are missing. Forecast results should be interpreted with caution. Missing weeks are kept as missing and are not automatically counted as zero cases.')
    if q['blank_observations']:
        messages.append('Some case counts were not reported. Blank values have not been changed to zero.')
    if q['week53']:
        messages.append('Week 53 was preserved from the source data.')
    if q['excluded_from_training']:
        messages.append('Some reporting is incomplete or not specified. These weeks are visible in the data but were not used for model training. Recent reports may still change.')
    if q['calendar_unknown_years']:
        messages.append('Please confirm the source reporting calendar before fitting across years.')
    messages.extend(friendly_reason(error) for error in q['errors'])
    return messages


def quality_details(dataset, limit=200):
    q = dataset['quality']
    names = {'missing_weeks': 'Missing weeks', 'blank_observations': 'Unreported case counts',
             'zero_case_weeks': 'Weeks reporting zero cases', 'duplicates': 'Repeated weeks',
             'week53': 'Week 53 observations', 'excluded_from_training': 'Weeks not used for training'}
    guidance = []
    if q['blank_observations'] or q['missing_weeks']:
        guidance.append(html.P('Unreported counts: you may confirm valid data with blanks. Obtain corrected counts from the source when possible and upload a revised file. Never replace an unknown count with zero. With a configured state-space missing-data policy, SARIMA may continue across gaps; NNAR requires enough complete residual lag windows, including its final lag window. If those are unavailable, the Hybrid remains unavailable and the reason is shown.'))
    if q['week53']:
        guidance.append(html.P('Week 53: preservation is informational and does not by itself prevent confirmation. Confirm each reporting year’s 52/53-week calendar from the source. A supplied week 53 conflicts with a declared 52-week year and must be reconciled with the source. The model also needs an explicit week-53 sequence policy; week 53 is never merged into week 52 or deleted to enable forecasting.'))
    return ([disclosure('How to proceed with missing counts and week 53', guidance)] if guidance else []) + [
        disclosure(f'{label} ({len(q[key])})', [
            *([html.P(f'Showing the first {limit} of {len(q[key])} findings. Full details are retained in Download Detailed Evidence on About.')]
              if len(q[key]) > limit else []), table(q[key], limit=limit)]) for key, label in names.items()]


def facts(dataset):
    meta = dataset['metadata']
    return {'Population': meta.get('population') or 'Not specified',
            'Case Classification': meta.get('case_classification') or 'Not specified',
            'Source': meta.get('source_system') or 'Not specified',
            'Reporting Status': meta.get('reporting_status') or 'Not specified',
            'Dataset Type': meta.get('dataset_type') or 'Not specified'}


def cards(values):
    return html.Div([html.Div([html.Span(label, className='card-label'), html.Strong(str(value), className='card-value')], className='fact-card numeric-card' if isinstance(value, Real) else 'fact-card metadata-card')
                     for label, value in values.items()], className='facts-grid')
