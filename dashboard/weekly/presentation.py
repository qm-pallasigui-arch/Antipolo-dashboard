"""Plain-language summaries shared by review and active-data views."""
from dash import html


def notice(text):
    return html.Div(text, className='message', role='status')


def disclosure(title, children):
    return html.Details([html.Summary(title), html.Div(children, className='disclosure-body')])


def table(rows, columns=None, limit=None):
    if not rows:
        return html.P('None recorded.', className='muted')
    columns = columns or {key: key if key.isupper() else key.replace('_', ' ').title() for row in rows for key in row}
    shown = rows[:limit] if limit else rows
    return html.Div(html.Table([
        html.Thead(html.Tr([html.Th(label) for label in columns.values()])),
        html.Tbody([html.Tr([html.Td('Not reported' if row.get(key) is None or row.get(key) == '' else str(row[key]))
                            for key in columns]) for row in shown]),
    ]), className='table-scroll', tabIndex=0)


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


def quality_details(dataset):
    q = dataset['quality']
    names = {'missing_weeks': 'Missing weeks', 'blank_observations': 'Unreported case counts',
             'zero_case_weeks': 'Weeks reporting zero cases', 'duplicates': 'Repeated weeks',
             'week53': 'Week 53 observations', 'excluded_from_training': 'Weeks not used for training'}
    guidance = []
    if q['blank_observations'] or q['missing_weeks']:
        guidance.append(html.P('Unreported counts: you may confirm valid data with blanks. Obtain corrected counts from the source when possible and upload a revised file. Never replace an unknown count with zero. With a configured state-space missing-data policy, SARIMA may continue across gaps; NNAR requires enough complete residual lag windows, including its final lag window. If those are unavailable, the Hybrid remains unavailable and the reason is shown.'))
    if q['week53']:
        guidance.append(html.P('Week 53: preservation is informational and does not by itself prevent confirmation. Confirm each reporting year’s 52/53-week calendar from the source. A supplied week 53 conflicts with a declared 52-week year and must be reconciled with the source. The model also needs an explicit week-53 sequence policy; week 53 is never merged into week 52 or deleted to enable forecasting.'))
    return ([disclosure('How to proceed with missing counts and week 53', guidance)] if guidance else []) + [disclosure(f'{label} ({len(q[key])})', table(q[key], limit=200)) for key, label in names.items()]


def facts(dataset):
    meta = dataset['metadata']
    return {'Population': meta.get('population') or 'Not specified',
            'Case Classification': meta.get('case_classification') or 'Not specified',
            'Source': meta.get('source_system') or 'Not specified',
            'Reporting Status': meta.get('reporting_status') or 'Not specified',
            'Dataset Type': meta.get('dataset_type') or 'Not specified'}


def cards(values):
    return html.Div([html.Div([html.Span(label, className='card-label'), html.Strong(str(value))], className='fact-card')
                     for label, value in values.items()], className='facts-grid')
