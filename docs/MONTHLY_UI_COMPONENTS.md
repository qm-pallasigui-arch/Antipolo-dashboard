# Monthly UI component library

The monthly application uses a navy text-only sidebar, a light top bar, teal accents and shared panel headers, adapted to the monthly ICD-10 study. Source/data semantics and authorization remain service concerns.

## Shared files

- `dashboard/monthly/components.py`: buttons, confirmation actions, badges, notices, section panels, metric cards/grids, empty states, page headings, disclosures, timestamps and tables.
- `dashboard/monthly/charts.py`: shared Plotly font, historical/forecast colors, zero markers and shaded availability gaps. HTML reports call the same chart builder.
- `dashboard/monthly/views.py`: module content composed from those components.
- `dashboard/monthly/ui.py`: shell, controls and server-authorized callbacks.
- `dashboard/assets/monthly.css`: scoped typography, colors, spacing, responsive layouts and component variants.

Dash and authenticated Flask pages use the same `application_shell` component tree from `components.py`; the Flask adapter serializes only its HTML components. Login retains its centered layout. Flask login/account/logout pages share this stylesheet through `/monthly-theme.css`. This public route serves only the fixed stylesheet; authenticated data routes remain protected.

## Design conventions

Use Segoe UI with system fallbacks. Page heading: 22px; section heading (including featured): 16px; body/control/table text: 14px; supporting text: 12px. Metric values use tabular numerals. Charts use the same font family.

Navy identifies the sidebar and the Dashboard ranking header; teal identifies primary actions and selected navigation. Dropdowns remain white. Secondary actions are outlined; rejection uses the danger variant. Notices support info, success, warning and error, always accompanied by text and a symbol. Status badges retain explicit wording rather than relying on color.

Sidebar selection uses a lighter navy fill and a flush teal bar with constant bold white link text; hover uses a weaker navy fill and never changes the selected treatment. An inset white keyboard-focus ring remains visible over every state; smaller muted uppercase labels group the navigation.

Tables display readable state labels while CSV/JSON retain canonical values. Unknown counts stay unknown; reported zeros remain numeric. Source signatures and long evaluation details use expandable disclosures.

The desktop Dashboard uses an 8/4 ranking and data-status row, one four-column KPI panel, a full-width chart, then an 8/4 estimates and warnings row. At 1200px the fixed 240px sidebar becomes an overlay; below 800px panels stack. The grid has no maximum width; gutters are 24px, or 16px below 800px. Prose is capped at 75ch. Disease Trends places annual history (5 columns) beside monthly records (7 columns), below its full-width chart. Forecasting places its saved chart (8 columns) beside estimates (4 columns), under a compact generation strip. At tablet widths Forecasting stacks so its chart and labeled controls retain room; Trends retains two table columns until 800px. Tables scroll within their panels. Empty dashboards retain the metric structure with “Not available” labels, never invented zeros.

## Usage

Model Performance leads with its plain-language evaluation summary and three metrics, then an 8/4 chart/comparison row that stacks below 1200px. The shared evaluation chart puts its legend below the plot to preserve mobile plotting width. Data & Quality places persistent upload/review controls beside active coverage in a 5/7 row (6/6 on tablets, stacked below 800px); viewers receive full-width coverage. Annotations remain with their form, followed by full-width provenance and normalized observations.

```python
section('Reporting coverage', [
    metric_grid([metric_card('Reported months', '96', 'Descriptive coverage count')]),
    message('City reports are unavailable for 2020 and 2022.', 'warning'),
])
```

Use `button(..., variant='secondary')` for supporting actions and `confirm_action` for activation/rejection. Confirmation callbacks must consume `submit_n_clicks`, never the wrapped button's raw click. Backend permission checks remain mandatory.

Add module layouts to views.py rather than duplicating CSS or table/chart helpers. Keep all new styles under monthly component classes. Avoid broad button selectors: dropdowns are also rendered as buttons.

Keyboard focus also covers custom elements with `tabindex`. Primary controls and mobile navigation use the existing 48px size; table sort controls get the same minimum for coarse pointers. Reduced-motion preferences disable CSS animations and transitions while status text remains visible. Notifications use a text label instead of an emoji.

Forecast counts and readable failure reasons stay visible; the batch reference is under the shared Run details disclosure. The elapsed timer has `aria-live="off"`. Shared Plotly styles in `charts.py` distinguish observed, baseline and hybrid series with solid, dotted and dashed lines. Model Performance includes a View comparison values disclosure with a table alternative to the chart.

Sign-in and password help reuse the shared auth panel, notices, navy/teal tokens and focus styles. A compact brand bar leaves Sign in as the only page heading; the centered card is 420px wide at most. Inputs and the full-width primary action are at least 48px high. The inline password toggle exposes its pressed state and changes its label. Native autocomplete, Caps Lock feedback and a disabled submitting state support keyboard and password-manager use. Input boundaries use the shared muted text color.

Forgot password sends an in-app notification visible only to administrators. The public response does not confirm account existence, and requests for the same account within 15 minutes are combined. Security / Accounts provides a password-reset disclosure requiring identity verification and confirmation; resetting revokes sessions and clears login failures. Administrators must use an established contact channel to verify identity and share the new password securely. This is assisted recovery, not automatic email delivery; an accessible administrator is required. Passwords are never included in notifications.

## Verification

`tests/browser_monthly.py` exercises the header, all modules, login/account styling, upload preview, cancel/accept activation dialogs, chart rendering, report download, mobile navigation and viewer restrictions with an isolated synthetic dataset. Routine screenshots are stored in `.artifacts/browser-monthly/`; selected historical verification remains in `evidence/` and the thesis evidence package.

The browser checks also exercise keyboard password toggling, notification navigation, sorting and comparison disclosure, plus focus styling, reduced-motion CSS and the forecast button's mobile height. These targeted checks are not a complete accessibility certification or a manual screen-reader review.

## UI review reconciliation — Phase 1 (8 November 2026)

Phase 1 changes are presentation-only. Annual history renders unavailable reporting as Unknown without modifying canonical observations or exported research data. The main ranking card shows valid results as an incomplete ranking, with one availability warning and a next step. Ranking references use the existing disclosure. Generation and chart-window controls are separated. Active coverage and upload preview use the same display adapter: absent blocks have a Not in upload badge and dashes; explicit observed zeros remain numeric.

Forecast outcomes use the shared display vocabulary in `components.py`. Identical saved error details are grouped in batch progress and Data & Quality; Notifications show the same saved detail without its internal status prefix. Distinct errors remain distinct. The local saved latest seven attempts were successful when inspected read-only. Existing browser logs identify the five synthetic-fixture failures as “No monthly observations supplied to the model workflow.” That evidence does not establish the identity or cause of an unspecified screenshot's original run.

| Item | Status | Evidence / remaining work |
|---|---|---|
| T1 | Done | Annual history renders 2020/2022 as Unknown; browser assertions cover both years. |
| D1 | Done | Valid partial results appear in the main ranking table; duplicate availability warnings removed. |
| F1 | Partial | Saved causes grouped and wording shared. Original screenshot run not identified; current local saved results have seven successes. |
| F2 | Done | Chart window has its own panel immediately before results; regeneration scope sits beside Generate. |
| F3 | Not applicable | Browser check finds 12 rows, January–December 2026, in the twelve-month table. Missing-row defect not reproduced. |
| X2 | Partial | Shared labels and readable error text applied to primary views, Notifications and HTML explanation; ranking reference disclosed. Comprehensive audit of advanced diagnostic/export text remains. |
| Q1 | Done | Coverage and pending-upload preview share badges/dashes for absent blocks; repeated coverage sentence removed from table rows. |
| X1 | Done | Full disclaimer stays in the shared footer; provisional notice is once near the top of result pages; duplicate dataset/coverage messages removed. |
| X3 | Done | Shared whole-count formatting, numeric header/cell alignment, trailing sort controls and 48px pagination targets. Native paginated sorting gains keyboard access. |
| X4 | Done | Notifications and Help & About hide the selector; other pages retain one visible selected-group label. |
| X5 | Done | Compact brand scale; Flask account/sign-out pages reuse navigation, footer and current-page styling. Both shells use the existing Notifications text label. |
| X6 | Done | Targeted browser measurements confirm 14px helper/metadata text and contrast above 4.5:1; upload hint raised from 12px to 14px. See Phase 2 measurements below. |
| X7 | Done | Create/reset password fields reuse the inline login toggle and shared styling; selects use existing control height and border color. |
| D2 | Done | Dashboard data-upload action is a text link. |
| D3 | Done | Plain-language estimate heading, two-column preview and explicit remaining-month count/link. |
| D4 | Done | Shared spacing separates tables from following content; chart axis says Calendar date. |
| T2 | Done | Reporting-gap bands have direct text labels independent of their colors. |
| T3 | Done | Monthly records use the existing disclosure, retaining all rows and paging. |
| F4 | Done | Forecast chart initially shows the preceding twelve months plus the chosen forecast window; keyboard-accessible radios restore full history. |
| M1 | Done | Comparison result and signed MAE improvement precede metrics. |
| M2 | Done | Undefined MASE is a note rather than an empty card; metrics include explanations. |
| M3 | Done | Held-out prediction chart has a descriptive title. |
| Q2 | Done | Annotation form and saved notes share one section with a role-aware empty state. |
| Q3 | Done | Grouped pending-upload actions distinguish withdrawal from rejection and explain their effects. |
| Q4 | Done | Annotation guidance is persistent text, not placeholder-only. |
| Q5 | Done | Help links to Data & Quality provenance rather than duplicating it. |
| R1 | Done | Each export has its description and download action in one shared card. |
| R2 | Done | Scope distinguishes selected-group data from overall rankings and explains full saved-month export. |
| N1 | Partial | Explicit run references group new forecast events, with counts and block names; coverage groups follow activation events. Historical failures lacking references remain separate rather than being assigned to guessed runs. |
| N2 | Done | Only unread items have an indicator, without an icon; filter labels use consistent capitalization. |
| N3 | Done | Mark-read requires confirmation and shows success feedback; cancellation is browser-tested. |
| H1 | Done | Help uses research-facing wording instead of the developer flag or Chapter 3 label. |
| H2 | Done | Glossary explains ICD-10 block, observed zero, MAE, RMSE and MASE. |
| S1 | Done | Save account is secondary and disabled until a select changes; reverting restores disabled state. Reset is secondary too. |
| S2 | Partial | Defect confirmed in an isolated database: self-demotion/self-disable are allowed when another active admin exists. Permission logic deliberately unchanged under the handoff's restriction. |
| S3 | Done | Role capabilities are explained and the page title is larger than section headings. |
| S4 | Done | Redundant location subtitle removed from account/sign-out pages. |
| S5 | Not applicable | Existing authentication has no forced-first-change state or workflow; temporary passwords were explicitly conditional on existing support. Current account creation is retained as the agreed limitation. |
| O1 | Done | Account-menu sign-out submits a CSRF-protected POST directly; running forecasts require confirmation with visible cancel. GET remains non-mutating and provides a no-JavaScript/recovery form. |

Fresh verification evidence is under `.artifacts/phase1-pytest.log`, `.artifacts/phase1-before-browser.log`, `.artifacts/phase1-after-browser.log`, `.artifacts/phase1-before/` and `.artifacts/browser-monthly/phase1-*.png`. The baseline and final browser runs passed; the final browser process returned exit code 0. Targeted pytest checks passed (34 tests, two existing Dash DataTable deprecation warnings). Pyflakes, documentation-link checks and `git diff --check` passed. The browser uses a synthetic upload, isolated accounts/database, and real prototype fitting; active accounts and datasets are not test fixtures. Intermediate runs exposed a misplaced test assertion and a mobile-navigation test helper that closed an already-open menu; both were corrected before the passing runs. Sandbox temporary-folder restrictions required elevated test execution, without repository permission changes.

Open verification work: manual screen-reader testing, a complete keyboard pass across every changed screen, measured contrast/touch-target audit (X3/X6), and complete paired before/after screenshots for every loading/error/empty state. Existing checks cover selected keyboard interactions, reduced motion, mobile layout and viewer restrictions; they do not establish full WCAG conformance. No new design tokens, dependencies, model parameters, evaluation splits or gap-handling rules were introduced.

Design rationale: Nielsen's system-status and error-prevention principles keep unknowns and actual failure causes explicit; visual hierarchy exposes the available ranking; Gestalt grouping separates generation from display controls; progressive disclosure keeps batch identifiers secondary. The review's proposed single cause must be derived from each saved run, rather than inferred from a generic status or assumed to apply to all datasets.

## Phase 2 — repetition and shared components (8 November 2026)

The six Phase 2 items above are implemented within the existing component/CSS system. No new dependencies or visual tokens were added. Header branding reuses the login's 16px scale and existing spacing tokens; navigation and footers match across Dash and authenticated Flask pages. Current Security/Sign out links expose `aria-current` in the Account menu. The existing text-only Notifications label replaces the Flask bell emoji, matching Dash without adding an icon dependency. Password policy, permissions and sign-out behavior remain unchanged.

Count display is rounded to whole numbers in both table types and HTML report tables; metric precision remains three decimal places. Stored forecasts, rank ordering, JSON/CSV data and model calculations retain their original precision. Static paginated-table styling lives in CSS; the component's only conditional cell style is alignment inferred from numeric column types. Dash's existing sort controls retain native sorting and receive keyboard activation, accessible names and a visible focus ring through the shared script/style. No custom table or paging engine was introduced.

| Measured element | Font size | Contrast / target size |
|---|---:|---:|
| Upload hint | 14px | 6.86:1 |
| Dataset source context | 14px | 7.17:1 |
| Metric helper | 14px | 7.17:1 |
| Notification timestamp | 14px | 7.17:1 |
| Footer | 14px | 6.61:1 |
| Security password help | 15px | 13.13:1 |
| Pagination buttons | — | 48 × 48px |

Measurements use rendered computed colors over the ancestor background and relative luminance, recorded in `.artifacts/browser-monthly/phase2-measurements.json`. The 14px reading scale and 48px targets are project conventions, not claims about WCAG minimum font size or a complete accessibility certification.

Fresh targeted pytest verification: 34 passed, two existing Dash DataTable deprecation warnings (`.artifacts/phase2-pytest.log`). Baseline and final browser runs passed (exit code 0). Baseline evidence is in `.artifacts/phase2-before-browser.log` and `.artifacts/phase2-before/`; revised screenshots/measurements are in `.artifacts/browser-monthly/phase2-*`, with the browser log at `.artifacts/phase2-after-browser.log`. Pyflakes, documentation-link checks and `git diff --check` passed. Intermediate visual checks found built-in Dash table CSS overriding alignment/layout and focus styling; the shared CSS now overrides those rules. The browser suite covers both roles, account toggles, sorting, notices, desktop/mobile layouts, loading/disabled forecast controls and real model execution against isolated synthetic data.

Remaining limitations at the Phase 2 checkpoint: manual screen-reader review, exhaustive keyboard traversal, full chart/control contrast audit, and paired before/after captures of every possible error/empty/loading combination were not complete. Phase 3 was subsequently authorized and is recorded below. No unresolved design questions or principle conflicts arose in Phase 2.

Design rationale: visual hierarchy removes repeated notices and reduces header prominence; Gestalt grouping keeps password inputs/toggles together; Jakob's Law uses consistent navigation and tables; recognition over recall keeps source context and one visible group selector while removing controls that do nothing.

## Phase 3 — per-screen improvements (8 November 2026)

The per-screen outcomes and remaining exceptions are recorded by ID above. Existing panels, tables, notices, disclosures, confirmation controls, radio styling and Plotly theme are reused. Forecast fitting, parameters, evaluation splits and source observations are unchanged. Failed forecast notifications now carry their saved run ID solely to support reliable event grouping. No dependency, schema or permission-policy change was introduced.

Fresh checks: 36 targeted tests passed, with two existing Dash DataTable deprecation warnings; the updated real-browser suite passed with isolated accounts/data and real prototype fitting. The new checks exercise keyboard history switching, annotation saving, grouped notifications, cancelled/confirmed mark-read, dirty account controls, forecast confirmation, and direct versus running-forecast sign-out. Server tests verify CSRF rejection, non-mutating GET, retained authentication while a running sign-out awaits confirmation, and session revocation after confirmed sign-out. Pyflakes and `git diff --check` passed.

Evidence: `.artifacts/phase3-pytest.log`, `.artifacts/phase3-before-browser.log`, `.artifacts/phase3-after-browser.log`, `.artifacts/phase3-before/`, and `.artifacts/browser-monthly/phase3-*`. Final desktop screenshots wait for the requested content page, avoiding captures with a new heading over content still updating. An initial run rejected an unsupported ARIA property on Dash's textarea; persistent help plus its supported title property replaced it before passing checks.

The security probe (`.artifacts/phase3-security-probe.py` and `.json`) used a disposable database with two administrators and confirmed both self-demotion and self-disable succeed. No production accounts were used. The handoff explicitly required reporting missing enforcement rather than silently changing permission logic, so this defect remains open. Forced first-login password changes also remain unsupported; adding that workflow needs a separate authorization/design pass.

The identified local app was restarted after checking that no local forecast batch was running. Runtime logs are `.artifacts/phase3-server.stdout.log` and `.artifacts/phase3-server.stderr.log`; `/healthz` is checked after restart. This is a local run, not cloud deployment.

Unverified: manual screen-reader behavior, exhaustive keyboard traversal, complete chart/control contrast measurement, and every error/loading/empty-state combination. Historical unlinked forecast notifications are not backfilled. Earlier source-identification and advanced-diagnostic wording limitations (F1/X2) remain. No original files, accounts or datasets were used as disposable fixtures; no changes were staged or committed.

Design rationale: visual hierarchy leads with useful results; progressive disclosure keeps records and diagnostics available without crowding the page; proximity groups annotations and exports with their actions; control and recovery provide explicit confirmation/cancel for forecast generation, notification state changes and sign-out during a run. Open implementation decisions: whether to authorize the S2 permission fix and a new forced-password-change workflow.

## Projected ranking card reconciliation (2026-11-08)

The owner approved disease-name-first rows, proportional bars and removing ranking sorting. The owner explicitly kept the selector above the card for consistency across pages. Established users/tasks, data, desktop/mobile contexts and accessibility requirements were reused: administrators generate forecasts; both roles inspect overall results; incomplete/empty states remain explicit. No new workflow, dependency, design token or modeling decision was needed.

| Item | Status | Evidence / implementation |
|---|---|---|
| H1 | Done | Shared section with existing teal top accent, 24px title and forecast-derived year; generated date is a secondary caption. |
| H2 | Done | Shared `ranked_list` component puts rank first, disease name before muted ICD code, and prominent values at right. |
| H3 | Done | Native decorative meters use rounded displayed totals and their maximum; printed values and accessible row labels remain. Synthetic browser checks cover ties, zero, single result and long mobile labels. No animation. |
| H4 | Done | First row alone uses the existing soft teal background. Other rows have equal emphasis. |
| H5 | Done | Estimated-consultations caption derives month/year endpoints from the saved forecast calendar. |
| H6 | Done | Primary and expanded ranking lists preserve repository order and expose no sort controls. The separate calculation-reference table retains its ordinary table behavior. |
| H7 | Done | Shared Provisional badge in the header when prototype mode is active. The full Dashboard notice remains once. |
| H8 | Not applicable | Owner explicitly retained selector position for consistency. Browser regression checks that it remains above the Dashboard card; UI shell was not changed. |
| H9 | Not applicable | Current ranking, selector, coverage tables and report builder already use dataset block `icd10_description`. Import preserves supplied casing while normalizing whitespace (`domain.py`). No separate capitalization rule was found. No labels, canonical data or exports changed. The original screenshot's exact dataset/version was not available to establish why its casing differed. |
| H10 | Done | Disclosure labels include group counts; ranking scope is directly beneath the title. |

Reused components: `section`, `badge`, `message`, `empty_state`, `disclosure`, `table` and `format_number`; the shared library now supplies the fixed-order ranked list. CSS uses existing palette and spacing tokens. Rankings, forecast values, source records, export code and model settings are unchanged. Titles say Projected ranking for incomplete/empty states; a saved incomplete ranking retains one availability warning and recovery instruction. Existing forecast loading/disabled behavior is unchanged.

Before/after synthetic component screenshots cover five-row, incomplete, empty (no saved ranking), unavailable (zero successes) and single-row states at 1200px and 390px in `.artifacts/ranking-card/`. These are controlled presentation fixtures, not screenshots of production results. `check_ranking_card.py` in `.artifacts/` verifies row labels/order, no ranking sort controls, tied/zero meter values, keyboard disclosure opening/closing and no mobile page overflow. Desktop and mobile five-row screenshots were visually inspected. The full application browser check additionally exercises real callbacks, the single provisional notice and unchanged selector placement.

Contrast evidence: `.artifacts/ranking-card/contrast.json`. Teal bar versus track **4.33:1**, first-row tint **4.86:1**, white surface **5.52:1**; ICD badge text **6.61:1**; Provisional badge and rank-one text **11.55:1**. Native meter pseudo-element computed colors are not exposed by Chromium, so their declared CSS tokens were resolved in the same rendered theme; screenshot inspection confirms the palette. Other text/background pairs use computed element colors. The checks exceed 3:1 for bars and 4.5:1 for text.

Verification: 36 relevant pytest tests passed (two existing Dash DataTable deprecation warnings), logged in `.artifacts/ranking-pytest.log`. Synthetic before/after Edge checks passed. The full application browser regression passed with no browser errors; evidence is `.artifacts/ranking-browser.log` and `.artifacts/browser-monthly/`. An initial browser run failed because a caption expectation was mistakenly changed on Forecasting; the expectation was corrected to apply only on Dashboard. Pyflakes and `git diff --check` passed.

Open questions and limitations: no outstanding design decision for this card. Manual screen-reader testing, cross-browser native-meter rendering and exhaustive keyboard traversal are unverified. Component fixtures supply the complete five-row state; real-model application tests use a two-success incomplete ranking. No new full production forecast was generated. The screenshot's original capitalization discrepancy remains unconfirmed; existing data labels were deliberately preserved. No disagreement with the approved design; H8 follows the owner's explicit exception.

Design Rationale: visual hierarchy makes the overall result dominant; recognition over recall keeps names, codes, units and provisional status visible together; progressive disclosure retains all totals and calculation references without competing with the headline result; Jakob's Law preserves the consistent selector location. Open design questions: none.

## Login, panel headers and Forecasting controls reconciliation (2026-11-09)

The owner approved a navy featured header, standard headers on Flask account/security panels, and amber Provisional badges. The established interview answers cover administrator/viewer tasks, saved data, forecast states, desktop/mobile use, keyboard accessibility and shared components. The primary action remains Generate forecasts and rankings. No new workflow or model choice was introduced. Login remains a separate heading treatment with a centered brand lockup; the lockup is not a heading.

| Item | Status | Implementation and evidence |
|---|---|---|
| L1 | Done | Shared password wrapper uses `:focus-within`; only its inner input outline is suppressed. The toggle retains its keyboard ring. Login/create/reset fields were checked; input and toggle are 48px high. |
| L2 | Done | Icon above a larger brand name; lockup and card centered as one unit, 16px gap, card capped at 420px. Login and password help checked at desktop and 375px; login empty/focused/error/submitting/caps-lock/toggle states exercised. |
| P1 | Done | `section()` now provides standard/featured variants and an optional right slot. Shared header classes supply the decorative CSS accent, divider, navy 16px standard title and responsive slot. Flask uses the shared library's `panel_header_markup` adapter and identical CSS. All eight module views checked. |
| P2 | Done | One featured result panel per module, verified in browser. Dashboard's ranking replaces its top border with the navy header; incomplete and empty-ranking titles remain accurate. On other modules, the first primary content panel receives the featured variant. Controls and secondary panels remain standard. |
| P3 | Done | Removed mint override; Provisional uses existing amber warning colors with symbol and text on a light background, including inside navy headers. |
| P4 | Done | Last-generated timestamp joins the ranking subtitle; overall scope and independence from the selected group remain visible. |
| P5 | Done | Read-only inspection of the active local dataset found A00-A09 stored as `Intestinal Infectious Diseases`. Importer preserves supplied casing. A shared live-UI display alias now renders this known name as `Intestinal infectious diseases` in ranking, selector, tables and Reports scope. Stored labels and downloaded exports deliberately retain source wording. This resolves the source question left open in H9. |
| F1 | Done | Generate title/scope text and button share one header row, stacking below 800px with a full-width button. Persisted progress and immediate action success/error feedback now appear within Forecast controls. Confirmation, server permissions and duplicate-submission prevention are unchanged. |
| F2 | Done | Separate Chart window panel removed. Saved forecast header contains labeled fieldsets and native radio controls; persistent explanatory caption remains. A display-options store preserves choices while content rerenders. No-forecast controls are disabled with an explanation. Arrow-key and click changes still update chart range and table months without changing saved results. |

Verification and evidence:

- Baseline application browser run passed: `.artifacts/headers-before.log`; original screenshots copied to `.artifacts/headers-before/` before edits.
- Final relevant pytest run: **36 passed**, two existing Dash DataTable deprecation warnings; `.artifacts/headers-pytest.log`.
- Final full browser run passed with **no browser errors**: `.artifacts/headers-after.log`. Checks include one featured panel per module, password-wrapper focus, no Chart window heading, controls inside the Saved forecast header, keyboard radio changes, unchanged persisted forecast counts, duplicate-submission prevention, feedback placement, exports, and viewer restrictions. Fresh screenshots are in `.artifacts/browser-monthly/`.
- Forecast screenshots cover no completed forecast (`headers-forecast-none*`), running (`phase2-forecast-processing`, `headers-forecast-running-mobile`), saved results/partial failures (`phase1-forecast-12-months`, `monthly-mobile`). All eight modules have fresh desktop and 375px captures; mobile Forecasting has its separate `monthly-mobile` capture. Keyboard focus smoke checks cover each module; these are not exhaustive traversal or screen-reader tests.
- Featured complete/incomplete/empty/unavailable/single-row ranking fixtures passed at desktop and 375px: `.artifacts/headers-ranking/`. These are controlled presentation fixtures, not production forecast evidence.
- Password help and reset-field focus/toggle checks passed using a disposable database: `.artifacts/check_security_headers.py`, `.artifacts/headers-security/`. No active account was changed.
- Contrast: white featured title on navy **13.13:1**; amber badge text/background **5.40:1**; teal password focus ring on white **5.52:1**. The decorative teal accent against white is also **5.52:1**. Radio focus uses teal against light chips and a white outer outline against navy. Evidence: `.artifacts/browser-monthly/phase2-measurements.json`, `.artifacts/headers-security/focus-contrast.json`, `.artifacts/headers-ranking/contrast.json`.
- Pyflakes, `git diff --check`, and documentation link checks passed. No dependencies, forecast parameters, ranking calculations, canonical data, export code or authorization rules changed. Nothing staged or committed.

Open questions and unverified items: no unresolved design decisions. Manual screen-reader behavior, cross-browser/native-meter rendering and exhaustive keyboard traversal remain unverified. Baseline mobile screenshots were 390px and do not cover every state at the exact requested 375px; final mobile captures use 375px. There is no matched pre-edit password-help/reset-focus screenshot or complete-ranking screenshot from this exact header baseline. Real-model browser coverage uses a two-success/five-failure synthetic dataset; no fresh seven-success production batch was run. Previously documented security self-account protection limitations are outside this presentation change.

Design Rationale: visual hierarchy distinguishes one primary result from standard panels; Gestalt proximity groups forecast controls, scope and feedback with their result; Nielsen's system-status and error-prevention principles retain visible progress and protected submissions; Jakob's Law keeps familiar labeled radios and consistent headers. No disagreement with the approved handoff. Open design questions: none.


## Layout overhaul ? Phase 1 (9 November 2026)

The owner confirmed the navigation groups, navy sidebar, 1200px overlay breakpoint, gutters, and header contents. The existing user tasks, admin/viewer permissions, data semantics, states, mobile needs and accessibility requirements complete the seven-topic interview. This phase changes the shared shell, Dashboard layout and Help quick fixes only; later page layouts await approval.

| Item | Status | Implementation and evidence |
|---|---|---|
| S1 | Done | One `application_shell` tree and Flask HTML adapter; sidebar, top bar, main and footer shared. Centered sign-in retained. |
| S2 | Done | Named navigation landmark, main/header/footer, first skip link, current-page attributes, 48px links, focus styling, overlay focus containment and Escape/close recovery. Targeted keyboard checks; manual screen-reader verification remains open. |
| S3 | Done | Dataset status and filename appear in the top bar once, alongside unread count and Account. Source provenance and upload-review metadata remain because they serve distinct tasks. |
| S4 | Done | Page titles use 22px on the page background. Selector is in the header and hidden on Help, Notifications and Data & Quality, whose content does not use the selected group. |
| S5 | Done | Shared 12-column grid with 8/4 and 12-column spans; 24px gap; no grid width cap. Four metrics share one panel with dividers. |
| S6 | Done | Removed automatic first-panel featuring from every module. Only Dashboard ranking (including empty/incomplete states) is featured; all panel titles are 16px. |
| S7 | Done | Featured band meets panel edges and follows the existing card radius. |
| S8 | Done | Help provenance link is inside About this study. Dashboard reporting-year caption is inside the warnings panel. |
| S9 | Done | Fixed sidebar at 1200px+, overlay below; two-column tablet reflow and stacked panels below 800px. Tables scroll within their containers. |
| S10 | Done | CSS overrides Dash's injected 100% graph height using the existing 500px chart height. Shared chart legend labels wrap. Estimates tables cap at 75ch; observed values provide a chart alternative. |
| S11 | Done | Browser navigation selectors use sidebar links; assertions cover landmarks, skip target, current page, featured count, hidden selectors, chart plotting height, and mobile overflow. |

Evidence is stored in `.artifacts/layout-phase1/`: `before/` and `after/` contain Dashboard, Help, Account and Signout captures at 1920, 1440, 1024, 768 and 375px; `after/` additionally captures the overlay open. These screenshots use a disposable synthetic dataset and do not represent production results. `after/contrast.json` and `after/measurements.json` record computed styles and page widths. `.artifacts/browser-monthly/` records empty, running, partial-failure, report and viewer flows.

Measured text contrast: sidebar white/navy and active navy/white **13.13:1**; featured white/navy **13.13:1**; top-bar navy/background **12.11:1**; notification-count navy/light-teal **10.82:1**. Teal against white is **5.52:1**, used for the active indicator on its white item and active-item focus. White sidebar focus against navy is **13.13:1**; teal focus against the page background is **5.10:1**. The active item also uses bold underlined text, so selection does not depend on color.

Open questions and unverified items: no unresolved design decisions. Manual screen-reader behavior, other browsers, physical touch devices and exhaustive keyboard traversal are unverified. The real-model browser fixture produces two successes and five expected failures; it is not evidence for a seven-success production batch. Later phases' internal page layouts remain intentionally unchanged. Shared shell migration includes authenticated Flask pages now; their account-management workflow layout remains Phase 5.

Design Rationale: visual hierarchy gives the page title priority and reserves the navy band for ranking; Gestalt proximity groups metrics and related panels; Nielsen's system-status principle keeps the dataset and model outcome visible; Jakob's Law supports familiar navigation, an Account disclosure and a recoverable mobile menu. No disagreement with the approved handoff; no open design questions.


## Layout overhaul ? Phase 2 (14 November 2026)

Disease Trends and Forecasting now use the approved shared grid. The seven interview topics are covered by the owner-approved handoff: researchers generate forecasts; viewers inspect data/results; primary actions, existing data, empty/loading/running/failure states, desktop/tablet/mobile use, keyboard/contrast/reduced motion and reusable components are established. No new design decision was needed. The monthly records table is visible beside annual history to support comparison; technical forecast disclosures remain collapsed.

| Item | Status | Phase 2 reconciliation |
|---|---|---|
| S1 | Done | Both pages reuse the Phase 1 shell. The earlier Save account failure did not reproduce in the isolated loaded-page probe or the full browser regression. The browser test now waits for the account page to finish loading before changing the role. |
| S2 | Partial | Shared landmarks/current-page labels retained. Skip-link, overlay Escape/focus recovery, table sorting and forecast-radio keyboard checks pass. Exhaustive keyboard traversal and manual screen-reader testing remain unverified. |
| S3 | Done | Shared top-bar dataset context retained; generation progress and saved-forecast dates retain their distinct meanings. |
| S4 | Done | Existing page-background heading and applicable disease selector retained; chart-window controls stay inside the Saved forecast header. |
| S5 | Done | Trends: full-width chart, then 5/7 annual-history/monthly-record panels. Forecasting: compact full-width generation strip, then 8/4 chart/estimates panels. Uses existing spacing tokens and shared sections/tables/controls. |
| S6 | Done | Both pages have zero featured panels; page titles remain 22px and panel headings 16px. Browser checks retain Dashboard-only featuring. |
| S7 | Not applicable | Neither Phase 2 page has a featured band; existing Dashboard band construction was not changed. |
| S8 | Done | Forecast coverage and latest-attempt feedback now sit inside Forecast availability; table descriptions and calculation details stay with their panels. |
| S9 | Done | Trends uses two tablet columns and stacks below 800px. Forecast panels stack below 1200px to preserve control/chart readability. No horizontal page overflow at 1920, 1440, 1024, 768 or 375px. |
| S10 | Done | Shared responsive Plotly helpers retained. Tests check actual Plotly width against its container and usable plot height above 150px at all five widths. Monthly observations and forecast estimates provide table alternatives. |
| S11 | Done | Updated monthly-record selectors for the now-visible table; added desktop column-position checks, chart-header control containment, five-width captures, plot resizing, and overlay recovery checks. |

Fresh verification: **36 pytest tests passed**, covering the monthly system and forecast batches; three existing Dash DataTable deprecation warnings. `tests/browser_monthly.py` passed with real synthetic forecasts (two successful groups, five expected missing-history failures), 24 persisted values, all 12 displayed forecast months, unknown annual periods, reported zeros, confirmation/cancel, duplicate prevention across tabs/refresh, progress and partial failures, exports, reduced motion and viewer access. No browser JavaScript errors were reported. The Phase 1 account dirty-state check passed in this run. This is fresh verification, not a reuse of the November 9 result.

Evidence: `.artifacts/layout-phase2/browser.log`, `pytest.log`, `before/`, and `after/`. Baseline screenshots cover Trends and the no-forecast Forecasting state at all five widths. Final captures include those states plus saved forecasts and open mobile/tablet overlays. `after/Forecasting-saved-measurements.json` and `after/Disease-Trends-measurements.json` record actual plotting dimensions. The November 12 saved-forecast baseline was interrupted; there is no matched saved-forecast before image, and no claim that the baseline batch completed.

Contrast measurements are in `after/contrast.json`: sidebar text and selected-item text **13.13:1**, top-bar text **12.11:1**, notification count **10.82:1**, standard panel headings **13.13:1**, and white Generate-button text on teal **5.52:1**. Existing focus/indicator colors remain teal on white (**5.52:1**), white on navy (**13.13:1**) and teal on the page background (**5.10:1**); current-page selection also has bold underlined text. No new color tokens were introduced.

Open questions and unverified items: no unresolved design requirements. Manual screen-reader behavior, exhaustive keyboard traversal, physical touch devices, other browsers and a seven-success production forecast batch remain unverified. The real-model fixture is synthetic. The interrupted saved-forecast baseline is unavailable. Phases 3?5 are not implemented by this change.

Design Rationale: visual hierarchy prioritizes the full-width trend and forecast chart; Gestalt proximity pairs each chart/history with its records or estimates; Nielsen's system-status and error-prevention principles keep real progress, latest failures and duplicate prevention visible; progressive disclosure keeps research and source details available without dominating the result. No disagreement with the approved Phase 2 handoff. Open design questions: none.

## Layout overhaul - Phase 3 (14 November 2026)

Implemented the approved Model Performance and Data & Quality layouts. All seven interview topics reuse established answers: administrator upload/review and viewer inspection tasks, existing primary actions and data, explicit unavailable/loading/failure states, desktop and mobile use, keyboard and contrast needs, and shared components. No new dependency, color token, model methodology, export behavior or permission rule was introduced.

| Item | Status | Phase 3 reconciliation |
|---|---|---|
| S1 | Done | Both pages retain the shared Dash/Flask shell. Persistent controls stay mounted so callback state survives navigation. |
| S2 | Partial | Shared landmarks, focus and overlay recovery retained; targeted keyboard checks pass. Manual screen-reader and exhaustive keyboard verification remain open. |
| S3 | Done | Active dataset context remains in the top bar; active coverage is distinct from pending upload preview. |
| S4 | Done | Page heading and applicable disease selector retained; Data & Quality remains independent of the selected disease. |
| S5 | Done | Model evaluation sentence and metrics precede chart 8/comparison 4. Upload/review 5 and coverage 7 precede annotations, provenance and normalized observations. |
| S6 | Done | Neither page has a featured panel. Standard headings and existing tokens are reused. |
| S7 | Not applicable | These pages have no navy featured band. |
| S8 | Done | Annotations remain beside their form in one panel; model warnings, run details and methodology are contained in Research details. |
| S9 | Done | Data columns reflow to 6/6 on tablets and stack on mobile; viewer coverage spans 12. Model panels stack below 1200px. Five-width checks find no page overflow. |
| S10 | Done | Shared evaluation chart retains unchanged values and series styles, with a horizontal legend below the plot. At 375px the plotting area is 195px wide and 300px high. Comparison and observation tables retain alternatives to charts. |
| S11 | Done | Browser checks cover coverage selectors, desktop panel geometry, summary order, viewer visibility, five widths, actual Plotly dimensions and usable plotting width. |

Fresh verification: **36 pytest tests passed**, with three existing Dash DataTable deprecation warnings. The full application browser regression passed without browser JavaScript errors, including real synthetic model execution, saved values, confirmation/cancel, duplicate prevention, exports and viewer restrictions. The mobile review caught a squeezed plot and clipped internal title; the shared evaluation helper now supplies the legend layout and the panel supplies the title. The full browser regression passed again after this correction.

Evidence: `.artifacts/layout-phase3/pytest.log`, `browser.log`, `before/` and `after/`. Baseline captures include both pages with no forecast and saved evaluation at 1920, 1440, 1024, 768 and 375px. Final saved-state captures and plotting measurements come from the full browser test. Fixtures use isolated databases and synthetic source data; two groups succeed and five have expected missing-history failures. Production accounts and datasets were not used as disposable fixtures.

The final responsive no-evaluation capture and account probe also passed (`after.log`); final empty-state and overlay captures, `measurements.json` and `contrast.json` are in `after/`. Measured text contrast: sidebar and standard headings 13.13:1, top bar 12.11:1, notification count 10.82:1, and Save note 5.52:1. Pyflakes and `git diff --check` passed; the edited document contains no local Markdown links to validate.

Manual screen-reader behavior, exhaustive keyboard traversal, physical touch devices, cross-browser rendering and a seven-success production forecast remain unverified. Existing security limitations documented above remain outside this presentation change. No changes staged or committed.

Design Rationale: visual hierarchy puts the evaluation result before its supporting detail; Gestalt proximity groups upload review with coverage and annotations with their form; Nielsen's system-status principle preserves active data and latest failed attempts; progressive disclosure keeps technical details available without dominating results. Open design questions: none.

## Phase 4 preparation (historical plan; implemented below)

Scope and requirements come from the approved handoff; no additional design interview is needed unless scope changes.

1. **Reports:** retain the existing three export cards and their download callbacks. Verify one desktop row, readable descriptions and mobile stacking; keep report scope and availability with their related content.
2. **Notifications:** place the existing persistent filters in a 3-column region beside the 9-column grouped list. Make filters sticky only on wide screens where they fit the viewport; stack on smaller screens. Preserve category/read filtering, grouping, unread counts, and mark-visible-read confirmation/cancel.
3. **Help & About:** arrange existing explanatory content in 8 columns and glossary/source links in 4. Keep provenance links inside a panel, no featured navy header, and no disease selector.

Reuse `section`, existing export cards, confirmation controls, disclosures, tables, the shared shell and CSS tokens. No new dependencies or changes to export contents, notification authorization or stored data are planned. Visual hierarchy prioritizes content; proximity keeps filters and supporting references beside their task; familiar controls and explicit feedback preserve recognition and recovery.

Acceptance checks: matched before/after captures at all five widths; no page overflow or sticky controls obscuring content; keyboard filter and disclosure use; unread/filter/empty states and mark-read cancel/accept; all three exports with administrator and viewer access; Help links and glossary readability; relevant pytest and full browser regression. Phase 5 account/security layout remains separate.


## Layout overhaul - Phases 4 and 5 (15 November 2026)

The owner requested completion of the remaining layout phases before the broader roadmap and explicitly chose "Layout plus prevent administrators demoting/disabling themselves." This closes the earlier S2 self-account defect; historical partial-status rows above describe their original review dates.

Phase 4 reuses the established interview answers: administrators and viewers export reports and inspect notifications/help; primary actions remain downloads and mark-visible-read; existing data, filters and report scope remain intact; loading, failure, empty and disabled states use the shared components; desktop/mobile widths and keyboard/focus/reduced-motion requirements remain unchanged. Phase 5 uses administrators' existing account creation, role/status management and verified password-reset tasks. The clarified permission restriction is enforced in the service as well as explained by disabled own-account controls. No new password-change workflow, dependency, palette or model methodology was introduced.

| Area | Final implementation |
|---|---|
| Reports | Existing three export cards remain in one desktop row and stack on mobile. Descriptions and buttons remain together; shared spacing and button alignment clarify the choices. Export scope and contents are unchanged. |
| Notifications | Persistent filters sit beside activity in a 3/9 desktop layout and stack below 1200px. A ResizeObserver enables sticky positioning only when the panel fits the viewport; position and spacing remain in CSS. Filter state survives navigation. Empty results and mark-visible-read confirmation/cancel retain existing behavior. |
| Help & About | Study/reporting/use/methodology panels occupy eight columns; glossary and source-provenance panels occupy four. Existing tablet/mobile rules reflow the content. No featured navy header or disease selector is added. |
| Security / Accounts | Create-user and manage-account panels use a 4/8 desktop layout and stack below 1200px. Each account's identity, role/status controls and reset disclosure are grouped together. Mobile fields stack so values remain readable. Create/save actions now provide a one-time success message; duplicate-account errors retain the alert. |
| Self-account protection | Administrators cannot demote or disable themselves, including through forged POSTs with another active administrator available. The server rejects the request without changing the account or revoking its session. A different administrator can still make the change under existing rules. Own role/status controls are disabled with visible explanation; password reset remains available. |

Reused components: `section`, `panel_header_markup`, shared shell, buttons, confirmation controls, disclosures, notices, export cards and existing grid/spacing/color tokens. The mounted notification controls stay outside replaced page content. Shared Plotly configuration and forecast/data calculations are unchanged.

The full pytest suite passed **68 tests**, with **1 skipped** dedicated Supabase test and seven existing Dash DataTable deprecation warnings (`pytest-final.log`). This includes three parameterized forged-self-account cases and create/update/duplicate feedback checks. The two stale presentation assertions now check documented whole-count formatting and the actual latest failure message, retaining small-error precision and failure visibility checks. Routine baseline/final captures and logs are in `.artifacts/layout-final/`. Intermediate expanded browser attempts stopped on an obsolete input selector and then an insufficient wait for dropdown opening. An isolated probe established keyboard opening followed by native option selection; the corrected test waits for the expanded state. The baseline run passed. Screenshot review also prompted mobile account-field stacking before final verification.

Completion confirmed on November 16 by inspecting the final November 15 run: `.artifacts/layout-final/acceptance-final.log` ends in PASS with no browser errors. That run includes five-width captures and geometry checks, keyboard notification filtering and persistence, empty results, confirmation/cancel, short-viewport sticky disabling, all three exports for both roles, self-account disabled controls, and the existing real synthetic forecast regression. Eight targeted presentation/data-quality tests also passed after the final Help source-link adjustment. Pyflakes, Markdown link checks and `git diff --check` passed. These are the recorded implementation-run results, not a claim that the entire suite was rerun on November 16. Phases 4 and 5 are complete for the agreed scope; broader roadmap work was not started.

Design Rationale: visual hierarchy distinguishes account creation and each task's primary action; Gestalt proximity keeps account controls and notification filters with their related content; progressive disclosure retains password resets and technical detail on demand; control and recovery preserves confirmations and adds server-side self-account protection. Open design questions: none for this scope. Manual screen-reader review, exhaustive accessibility certification, physical-device/cross-browser testing and the broader roadmap remain separate work.

## Accessibility and interaction sprint (16 November 2026)

The owner's request for the next sprint starts the first broader roadmap item after layout Phases 4 and 5. The seven interview topics reuse established administrator/viewer tasks, primary actions, existing data and states, desktop/mobile use, keyboard and assistive-technology needs, and shared heading/notice/disclosure components. No material design questions remain.

- Navigation focuses the shared page heading after both the new heading and content render. Routine polling, filters and downloads do not request focus changes.
- Forecast progress separates the elapsed timer from the live notice. When only elapsed time changes, the callback preserves the summary subtree, expanded Run details and keyboard focus. Meaningful progress or failure changes still update the existing status/alert notice; no fabricated percentages are introduced.
- Input, select, textarea and Dash dropdown boundaries reuse the existing muted-text color token, measuring 7.17:1 against white. The password field retains its existing wrapper treatment. No new palette or component was added.
- Shared notices wrap long unbroken error text. A rejected upload with a 300-character invalid code remains readable at 375px without page overflow.

Fresh verification: **69 pytest tests passed, 1 dedicated Supabase test skipped**, with seven existing Dash DataTable deprecation warnings. The full browser regression exited successfully with no browser errors, including real synthetic model execution, existing five-width checks, navigation-heading focus, long mobile errors and preserved disclosure focus across an elapsed-time update. The new callback test also verifies that an unchanged progress token omits the summary update and a subsequent failure supplies its actionable message. Pyflakes passed.

Evidence: `.artifacts/accessibility-sprint/pytest.log`, `browser.log` and `contrast.json`; mobile error screenshot `.artifacts/browser-monthly/accessibility-long-error.png`. Nine measured color pairs meet the project's respective text or line/control thresholds: chart series 6.60:1, 4.28:1 and 4.18:1; chart text 13.13:1; control boundary 7.17:1; notice text 5.83:1 or higher. These are selected measurements, not an exhaustive contrast audit. Existing series styles and table alternatives remain unchanged.

Manual acceptance remains open: with a screen reader, verify the new page heading is announced after navigation, meaningful forecast updates and errors are announced, elapsed ticks do not repeat the notice, and Run details remains usable during progress. Exhaustive keyboard traversal, physical touch devices and other browsers remain unverified. Automated DOM/focus checks do not establish spoken output or full WCAG conformance. Durable execution, performance/deployment and research handoff were not started in this sprint.

Design Rationale: Nielsen's system-status principle keeps meaningful progress available without repeated timer announcements; control and recovery preserves the user's focus and disclosure state; visual hierarchy makes controls identifiable using existing tokens. Open design questions: none; manual accessibility acceptance remains pending.

## Durable forecast execution sprint (16 November 2026)

The owner requested finishing the next sprint and preparing the following one. All seven interview topics reuse established requirements: administrators generate/cancel forecasts; viewers inspect saved progress/results; generation stays the primary action; existing seven-group data and real progress remain intact; queued/running/cancelling/completed/partial/failed/interrupted states are explicit; desktop/mobile and keyboard needs remain unchanged; notices, buttons, confirmation dialogs, disclosures and tables reuse the existing components and CSS tokens. Cancellation retains completed values and earlier rankings; interrupted work requires an explicit rerun. No dependency, palette or model-methodology change was introduced.

The generation callback now submits to a persistent database queue and returns immediately. A separate worker supervises the model process and its descendants. Administrators can cancel a queued or running batch through a confirmation dialog; dismissing it leaves the job running. The confirmation captures the batch ID when opened, so a stale dialog cannot cancel its replacement. The server rejects viewer cancellation. The Generate action stays disabled while queued, running or cancelling. Terminal progress includes the saved ranking summary; timers retain the prior sprint's focus-preserving behavior.

Run details shows the latest 20 batch summaries for the current dataset/configuration, with all new records retained in storage. Visual review found that the disclosure's inherited word-wrapping squeezed table headers on mobile. The history region now uses normal wrapping and the existing keyboard-accessible horizontal table scroll. No new sizing or color values were needed. New submissions clear stale cancellation feedback. Existing loading, empty, failure, disabled, reduced-motion and focus behavior remains in use.

Fresh verification: the full suite passed **81 tests, 1 skipped** dedicated Supabase test, with seven existing Dash DataTable warnings (`.artifacts/durable-sprint/pytest-acceptance.log`). After the final supervisor-query adjustment and an additional abrupt-owner-loss test, **20 lifecycle tests passed** (`lifecycle-final.log`). These counts overlap; they are not 101 distinct tests. Lifecycle checks cover persistent queue/history, competing claims, request return without fitting, forbidden viewer cancellation, completed-value retention, atomic ranking/cancellation, stale leases, deadline/dataset/shutdown stops, child crashes and Windows descendant cleanup after abrupt supervisor loss.

The final full browser regression passed with no browser errors (`.artifacts/durable-sprint/browser-verified.log`). It covers confirmed cancellation and dismissal, rerun, refresh/second-tab progress, real synthetic Prophet/XGBoost output (24 saved values, two successes and five expected missing-history failures), unavailable Top Five, roles/exports, five-width layouts, keyboard history scrolling and retained progress focus. Earlier attempts exposed an asynchronous-dialog test wait and an obsolete completion-message selector; both were corrected before the final run. The mobile history correction was then verified in a fresh full run. Screenshots remain in `.artifacts/browser-monthly/` and the existing layout artifact directories. The real app also returned HTTP 200 from `/healthz` on port 8050 using an isolated database, started its worker automatically, and stopped that worker after its launcher exited.

Local implementation acceptance is complete. Linux container execution/signals, live PostgreSQL concurrency/recovery and backup/restore remain the prepared Sprint 3 checks in `SUPABASE_MIGRATION.md`; Docker was unavailable in this shell and no dedicated PostgreSQL URL was used. Manual screen-reader, exhaustive keyboard and physical-device/cross-browser acceptance remain open. No production accounts/datasets were test fixtures; nothing was committed or deployed.

Design Rationale: control and recovery adds explicit cancellation without losing completed records; Nielsen's system-status principle exposes durable queue and terminal states; progressive disclosure keeps retained batch history available without crowding the primary result. Open design questions: none.
