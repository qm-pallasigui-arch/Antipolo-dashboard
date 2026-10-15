"""Deterministic, source-linked briefings built from existing weekly forecasts."""
import math
from datetime import datetime, timezone, timedelta
from io import BytesIO
from xml.sax.saxutils import escape

SOURCES = {
    'Dengue': {
        'title': 'DOH CAR: Dengue surveillance and response coordination (Enhanced 4S)',
        'url': 'https://caro.doh.gov.ph/coordination-meeting-and-situation-updating-in-connection-with-dengue-surveillance-and-response/',
        'action': 'Coordinate removal of mosquito breeding sites and reinforce personal protection and early-consultation messages. Assess vector-control needs through the local surveillance team; a projection alone does not trigger fogging.',
        'indicator': 'Sites checked for breeding sources; prevention sessions delivered.',
    },
    'Measles-Rubella': {
        'title': 'DOH National Immunization Program, Booklet 2: Vaccine-Preventable Disease Surveillance, Chapter 3, E.2',
        'url': 'https://doh.gov.ph/wp-content/uploads/2023/08/Booklet-2-Vaccine-Preventable-Diseases-and-Vaccine-Preventable-Disease-Surveillance.pdf',
        'action': 'Review case-notification, investigation and specimen-referral readiness with CESU. For actual suspected cases, follow immediate notification and investigation/specimen collection within 48 hours of notification under the cited guidance; do not wait for a projected peak.',
        'indicator': 'Notification and specimen-referral arrangements reviewed; timeliness of actual case investigations.',
    },
    'Leptospirosis': {
        'title': 'DOH Ilocos: Leptospirosis prevention advisory, August 27, 2026',
        'url': 'https://ro1.doh.gov.ph/?p=4279',
        'action': 'Where flood exposure is documented, reinforce avoidance of floodwater, protective footwear and prompt health-center assessment. Medication or prophylaxis requires individual clinical assessment, not a forecast trigger.',
        'indicator': 'Exposure-prevention messages delivered; referral arrangements reviewed.',
    },
}


def week_label(point, offset=None):
    if point.get('year') and point.get('morbidity_week'):
        return f"{point['year']} W{int(point['morbidity_week']):02d}"
    return f"Forecast week +{offset or point.get('horizon_week', '?')}"


def build_report(active, result, disease, horizon):
    if horizon not in (4, 13, 26, 52):
        raise ValueError('Choose a 4, 13, 26 or 52 week outlook.')
    if not active or not active.get('records'):
        raise ValueError('Upload and confirm weekly records in Data first.')
    if not result or result.get('dataset_id') != active.get('id') or result.get('disease') != disease:
        raise ValueError('Generate a forecast for this disease and current dataset in Forecast, then return to Reporting.')
    values = (result.get('hybrid') or [])[:horizon]
    index = result.get('forecast_index') or []
    if len(values) != horizon or len(index) < horizon or any(not math.isfinite(float(v)) or v < 0 for v in values):
        raise ValueError('A complete, valid Hybrid forecast is required for the selected outlook. Review Forecast.')
    meta = active.get('metadata', {})
    complete = [r for r in active['records'] if r['disease'] == disease and r.get('case_count') is not None
                and str(r.get('reporting_status') or meta.get('reporting_status', '')).lower() == 'complete']
    if not complete:
        raise ValueError('No complete observed week is available for the comparison baseline.')
    baseline = max(complete, key=lambda r: (r['year'], r['morbidity_week']))
    base = float(baseline['case_count'])
    if not math.isfinite(base) or base < 0:
        raise ValueError('The latest complete week has an invalid case count.')
    rows = []
    for i, value in enumerate(values):
        change = float(value) - base
        rows.append({'week': week_label(index[i], i + 1), 'cases': float(value), 'change': change,
                     'percent': change / base * 100 if base else None,
                     'status': 'Above baseline' if change > 0 else 'Below baseline' if change < 0 else 'At baseline'})
    above = [r for r in rows if r['change'] > 0]
    peak = max(rows, key=lambda r: r['cases'])
    summary = (f"{len(above)} of {horizon} projected weeks exceed the latest complete week "
               f"({week_label(baseline)}: {base:g} cases). "
               f"The projected total is {sum(values):,.1f} cases, with a peak of {peak['cases']:,.1f} in {peak['week']}. "
               + (f"The first above-baseline week is {above[0]['week']}." if above else 'No projected week exceeds this baseline. Continue routine surveillance.'))
    blocks = []
    for i in range(0, horizon, 4):
        part = rows[i:i + 4]
        blocks.append(f"{part[0]['week']} to {part[-1]['week']}: {sum(r['cases'] for r in part):,.1f} projected cases; "
                      f"{sum(r['change'] > 0 for r in part)} of {len(part)} weeks above baseline.")
    source = SOURCES.get(disease)
    finding = f"First projected increase: {above[0]['week']}." if above else 'No above-baseline weeks projected.'
    actions = [dict(finding=finding, activity='Review the latest complete reports, reporting delays and local case information before adapting preparedness activities.',
                    owner='City health officer / CESU', timing='At report review; repeat when new weekly data arrive',
                    indicator='Weekly records reviewed and discrepancies followed up.', reference='Application planning suggestion')]
    if source:
        actions.append(dict(finding=finding, activity=source['action'], owner='City health office and relevant disease program team',
                            timing=f"Prepare before {above[0]['week']}; review weekly" if above else 'Maintain routine preparedness; review weekly',
                            indicator=source['indicator'], reference='DOH reference [1]; timing and indicators are planning suggestions'))
    else:
        actions.append(dict(finding='No verified disease-specific guidance is configured.', activity='Ask the relevant disease program team to identify applicable DOH/local guidance before selecting disease-specific interventions.',
                            owner='City health officer / disease program team', timing='Before issuing disease-specific recommendations',
                            indicator='Applicable guidance identified.', reference='Application planning suggestion'))
    limitations = [
        'Projected increases are comparisons with one observed week, not outbreak declarations or verified alert-threshold crossings.',
        'The outlook begins after the model data cutoff, not necessarily the current calendar week. Confirm data freshness before operational use.',
        'Forecasts do not establish causes, barangay hotspots or individual clinical decisions. Lower projections do not exclude an outbreak.',
        'Intervention timing, proposed teams and follow-up indicators are application planning suggestions, not DOH mandates. No Antipolo-specific protocol has been verified.',
        'Any displayed model range is provisional, not a validated confidence interval. Longer outlooks should be reassessed as new observations arrive.',
    ]
    limitations += [str(w) for w in result.get('warnings', [])]
    limitations += [str(w) for w in active.get('eligibility_reasons', [])]
    if not base:
        limitations.append('Percentage changes are unavailable because baseline cases equal zero.')
    return dict(dataset_id=active['id'], disease=disease, horizon=horizon, issued_at=result.get('issued_at'),
                generated_at=datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M PHT'),
                population=meta.get('population') or 'Not specified', location=meta.get('location') or 'Not specified',
                classification=meta.get('case_classification') or 'Not specified', source_file=meta.get('source_file') or 'Not specified',
                source_date=meta.get('source_date') or 'Not specified', context=result.get('context', active.get('context', '')),
                configuration=result.get('configuration_label') or 'Not specified', baseline_week=week_label(baseline),
                baseline=base, rows=rows, summary=summary, blocks=blocks, actions=actions,
                limitations=list(dict.fromkeys(limitations)), sources=[source] if source else [])


def weekly_cells(report):
    return [[r['week'], f"{r['cases']:,.1f}", f"{r['change']:+,.1f}",
             f"{r['percent']:+.1f}%" if r['percent'] is not None else 'N/A', r['status']] for r in report['rows']]


def report_pdf(report):
    """Render the same report payload as a paginated A4 briefing."""
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.graphics.shapes import Drawing, Line, String, PolyLine

    stream = BytesIO()
    styles = getSampleStyleSheet()
    styles['BodyText'].fontSize = 9
    styles['BodyText'].leading = 13
    def p(value, style='BodyText'):
        return Paragraph(escape(str(value)), styles[style])
    flow = [p('Disease Outlook and Preparedness Briefing', 'Title'), p(report['disease'], 'Heading1')]
    for key, label in [('generated_at', 'Prepared'), ('context', 'Context'), ('location', 'Location'), ('population', 'Population'),
                       ('classification', 'Case classification'), ('source_file', 'Source'), ('source_date', 'Source date'),
                       ('baseline_week', 'Latest complete week'), ('issued_at', 'Forecast issued'), ('configuration', 'Model protocol')]:
        flow.append(p(f'{label}: {report[key]}'))
    flow += [p(f"Outlook: {report['horizon']} weeks | Baseline: {report['baseline']:g} cases"),
             p('Executive summary', 'Heading2'), p(report['summary']), p('Weekly outlook', 'Heading2')]
    drawing = Drawing(480, 165)
    maximum = max([report['baseline']] + [r['cases'] for r in report['rows']] + [1]) * 1.1
    points = []
    for i, row in enumerate(report['rows']):
        points.extend([35 + i * 420 / max(1, len(report['rows']) - 1), 30 + row['cases'] / maximum * 115])
    drawing.add(Line(35, 30, 455, 30, strokeColor=colors.grey))
    drawing.add(Line(35, 30, 35, 150, strokeColor=colors.grey))
    drawing.add(PolyLine(points, strokeColor=colors.HexColor('#185FA5'), strokeWidth=2))
    baseline_y = 30 + report['baseline'] / maximum * 115
    drawing.add(Line(35, baseline_y, 455, baseline_y, strokeColor=colors.HexColor('#b45309'), strokeDashArray=[4, 3]))
    drawing.add(String(0, 140, f'{maximum:.0f}', fontSize=8))
    drawing.add(String(20, 28, '0', fontSize=8))
    drawing.add(String(35, 12, report['rows'][0]['week'], fontSize=8))
    drawing.add(String(455, 12, report['rows'][-1]['week'], fontSize=8, textAnchor='end'))
    flow += [drawing, p('Blue: projected weekly cases. Dashed amber: latest complete week baseline. Values below are rounded for display.')]
    data = [[p(x) for x in ['Week', 'Projected cases', 'Case change', '% change', 'Comparison']]]
    data += [[p(x) for x in row] for row in weekly_cells(report)]
    grid = Table(data, colWidths=[105, 90, 85, 75, 125], repeatRows=1, hAlign='LEFT')
    grid.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8eff8')),
                              ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
                              ('LINEBELOW', (0, 0), (-1, -1), .3, colors.lightgrey)]))
    flow += [grid, p('Interpretation by period', 'Heading2')]
    flow += [p(b) for b in report['blocks']]
    flow.append(p('Recommendations and suggested intervention plan', 'Heading2'))
    for i, action in enumerate(report['actions'], 1):
        flow.append(p(f'Action {i}', 'Heading3'))
        for key, label in [('finding', 'Finding'), ('activity', 'Activity'), ('owner', 'Proposed team'), ('timing', 'Timing'), ('indicator', 'Follow-up indicator'), ('reference', 'Basis')]:
            flow.append(p(f'{label}: {action[key]}'))
        flow.append(Spacer(1, 8))
    flow.append(p('Evidence and limitations', 'Heading2'))
    flow += [p(item) for item in report['limitations']]
    flow.append(p('References', 'Heading2'))
    for i, source in enumerate(report['sources'], 1):
        flow += [p(f"[{i}] {source['title']}"), p(source['url'])]
    if not report['sources']:
        flow.append(p('No verified disease-specific reference configured.'))
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.drawString(42, 25, 'Preparedness briefing | Suggested plan for city health officer review')
        canvas.drawRightString(A4[0] - 42, 25, f'Page {doc.page}')
        canvas.restoreState()
    SimpleDocTemplate(stream, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=45,
                      title=f"{report['disease']} - Disease Outlook", author='Antipolo Disease Forecasting').build(flow, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()
