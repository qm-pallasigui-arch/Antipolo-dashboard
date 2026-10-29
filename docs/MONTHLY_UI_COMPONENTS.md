# Monthly UI component library

The monthly application uses the old dashboard's navy header, teal accents, compact navigation and card hierarchy, adapted to the monthly ICD-10 study. Source/data semantics and authorization remain service concerns.

## Shared files

- `dashboard/monthly/components.py`: buttons, confirmation actions, badges, notices, section panels, metric cards/grids, empty states, page headings, disclosures, timestamps and tables.
- `dashboard/monthly/charts.py`: shared Plotly font, historical/forecast colors, zero markers and shaded availability gaps. HTML reports call the same chart builder.
- `dashboard/monthly/views.py`: module content composed from those components.
- `dashboard/monthly/ui.py`: shell, controls and server-authorized callbacks.
- `dashboard/assets/monthly.css`: scoped typography, colors, spacing, responsive layouts and component variants.

Flask login/account/logout pages share this stylesheet through `/monthly-theme.css`. This public route serves only the fixed stylesheet; authenticated data routes remain protected.

## Design conventions

Use Segoe UI with system fallbacks. Desktop title: 28px; page heading: 22px; section heading: 16px; body/control/table text: 14px; supporting text: 12px. Metric values use tabular numerals. Charts use the same font family.

Navy identifies the application header; teal identifies primary actions and selected navigation. Dropdowns remain white. Secondary actions are outlined; rejection uses the danger variant. Notices support info, success, warning and error, always accompanied by text and a symbol. Status badges retain explicit wording rather than relying on color.

Tables display readable state labels while CSV/JSON retain canonical values. Unknown counts stay unknown; reported zeros remain numeric. Source signatures and long evaluation details use expandable disclosures.

The desktop Dashboard places the chart beside data status and source freshness. Below 800px, navigation becomes an expandable menu and panels stack. Tables scroll within their panels. Empty dashboards retain the metric structure with “Not available” labels, never invented zeros.

## Usage

```python
section('Reporting coverage', [
    metric_grid([metric_card('Reported months', '96', 'Descriptive coverage count')]),
    message('City reports are unavailable for 2020 and 2022.', 'warning'),
])
```

Use `button(..., variant='secondary')` for supporting actions and `confirm_action` for activation/rejection. Confirmation callbacks must consume `submit_n_clicks`, never the wrapped button's raw click. Backend permission checks remain mandatory.

Add module layouts to views.py rather than duplicating CSS or table/chart helpers. Keep all new styles under monthly component classes. Avoid broad button selectors: dropdowns are also rendered as buttons.

## Verification

`tests/browser_monthly.py` exercises the header, all modules, login/account styling, upload preview, cancel/accept activation dialogs, chart rendering, report download, mobile navigation and viewer restrictions with an isolated synthetic dataset. Screenshots and output are stored in `evidence/monthly-*.png` and `evidence/monthly-ui-browser.txt`.
