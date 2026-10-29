# UI refresh and operational metric update

The weekly app now has a navy identity header, an accurate dataset-state badge,
sticky icon-and-label navigation, keyboard-accessible tabs, and shared typography.
All five destinations remain visible on mobile. Numeric upload summaries use the
same 28px type; metadata uses a separate card treatment. Numerical table cells are
right-aligned with tabular numerals.

## Changed implementation

- `dashboard/weekly/ui.py`: header, navigation labels, dataset badge, shared upload
  counts, three-metric evaluation tables with units and nonzero MAPE coverage.
- `dashboard/weekly/presentation.py`: numerical versus metadata cards and table alignment.
- `dashboard/assets/revision39.css`: consolidated base rules and responsive design tokens.
- `dashboard/assets/navigation.js`: tab semantics, roving focus, arrows, Home/End,
  Enter/Space activation. Existing modal focus behavior is preserved.
- `dashboard/modeling/metrics.py`: operational MAE/RMSE/MAPE scoring only.
- `dashboard/modeling/historical_metrics.py` and `pipeline.py`: isolated historical
  monthly scoring compatibility; its selection behavior remains unchanged.
- `dashboard/weekly/result_schema.py`, `outputs.py`, and UI boundaries: normalize
  older metric records before display, cached reuse, exports, and new snapshots.
  Original session inputs, source records, and existing snapshots are not rewritten.
- `WEEKLY_SYSTEM.md`: updated operational metric description.

## Validation

- Full regression suite: **232 passed**, with 10 pre-existing Dash DataTable
  deprecation warnings. Command: `python -m pytest -q -p no:cacheprovider
  --basetemp=evidence/pytest-ui-20261009-full`.
- A real deterministic weekly fit using old versus new scoring produced identical
  forecast arrays, uncertainty ranges, diagnostics, and retained metrics after
  excluding the issue timestamp and removed metric. The fixture includes a missing
  holdout observation. This establishes invariance for that fixture, not a new
  claim about predictive accuracy.
- Regression cases cover zero and mixed actuals, older cached results, nested
  exports, diagnostics, and new snapshots. Historical monthly regressions pass.
- Edge/Chromium browser checks at 1440x1000 and 390x844: all five pages, active
  navigation, keyboard focus, sticky navigation, single H1, rendered charts,
  horizontal overflow, accurate dataset badges, upload typography and modal focus.
  No JavaScript page errors.
- Existing upload-recovery browser test also passes: progress, validation failure,
  form/data preservation, corrected retry, and mobile rendering.
- Screenshots and browser report: `evidence/ui-refresh-2026-10-09/`.
  Separate recovery evidence: `evidence/source-recovery-ui-2026-10-09/`.

## Historical references retained

WAPE remains only where needed for historical compatibility or evidence:

- `dashboard/modeling/historical_metrics.py`: historical calculation.
- `dashboard/modeling/pipeline.py`: archived monthly selection policy.
- `dashboard/callbacks/view_callbacks.py`: historical monthly display/export consumers.
- `dashboard/config.py`: deprecated historical threshold.
- Historical regression fixtures in `tests/test_modeling.py`, `tests/test_callbacks.py`,
  and `tests/test_provenance.py`.
- Archived reports, prior handoffs, changelog history, and existing evidence and
  reconciliation artifacts. These were not rewritten.
- `dashboard/weekly/result_schema.py` and transition tests recognize the old key
  solely to remove it from operational outputs.

Preview: http://127.0.0.1:8065 (local development server; no deployment performed).
Existing uncommitted upload-recovery changes were preserved.

## Review overview follow-up

The review dialog now begins with a report containing included/excluded worksheet
names, links to their previews, the missing-value integrity statement, and all
current data notices. Counts come from the prepared dataset. Section links move
focus to the destination inside the dialog. The three numbered headings share
18px, weight-700 styling. Cancel and formerly borderless secondary actions have
visible borders.

Data-check previews are prepared when the pending dataset or review mode changes,
not on each disclosure toggle. Each finding category renders at most 20 preview
rows, with an explicit truncation notice and the full-evidence download location.
Counts and stored evidence remain complete. Opening/reopening section 3 therefore
does not post the dataset again. This is not a reduction in validation coverage.

Validation: 57 affected regression tests passed. Desktop/mobile browser checks
verified the inventory, jump links, matching section typography, bordered Cancel,
no horizontal dialog overflow, and zero expansion requests. The measured local
open handler took 4ms on the test fixture; this is not an end-to-end performance
guarantee. Evidence: `evidence/review-overview/`.

## Navigation and scroll follow-up

- Include/Exclude remains a bordered selected-state control but is compact again.
- Sticky review reminders use amber, dark text, and a warning icon.
- Removed the preview-text-change scroll reset. Worksheet selection changes retain
  the selected worksheet's viewport position and radio focus. New dialog openings
  still start at the top.
- Empty Overview, Forecast, and Trends views provide a direct upload shortcut.
- Source-related forecast failures provide a direct Source information shortcut:
  switch to Data, open the existing edit flow, then scroll/focus section 2. No source
  metadata is automatically changed and evidence validation is retained.
- Overview, Forecast, Trends, Data, and About use shared section-heading treatment;
  Forecast separates status/action, outlook, and historical performance.

Validation: 57 affected regression tests passed. Browser acceptance verified all
three empty-state shortcuts, incomplete-reporting forecast recovery navigation,
compact controls, amber reminders, desktop/mobile selection scroll preservation,
and focus below the sticky bar. Measured worksheet displacement was 0.3125px for
each include/exclude toggle in the fixture. No browser page errors.
Evidence: `evidence/navigation-followup/`.
