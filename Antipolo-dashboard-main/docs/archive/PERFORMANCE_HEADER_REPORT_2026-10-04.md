# Header and source-update performance — 4 October 2026

The header now uses a responsive teal title panel, an Antipolo identity block, concise purpose text, and restrained context tags. It contains no invented statistics, live-status claims, or decorative forecast data. Desktop and mobile layouts retain the established navigation.

Profiling the local 1,590-observation workbook identified duplicate processing: source-information updates unfolded the original workbook again and performed five validations; subsequent unchanged confirmation repeated that work. Updates now retain mappings/source evidence and recheck prepared records directly. Unchanged facts reuse the validated pending dataset. Source corrections, reporting/calendar validation, and active/pending isolation remain enforced.

Collapsed data-check tables are now created only when the checks section is expanded. Opening those details does not rebuild the editable form.

| Local measurement | Before | After |
| --- | ---: | ---: |
| Profiled source-information update | 227.6 ms | 169.5 ms |
| Serialized initial review response | 177,724 bytes | 88,093 bytes |
| Unchanged confirmation's source-fact processing | Repeated validation | About 0.02 ms |

These are single-run local backend/payload measurements, not a guaranteed end-to-end latency improvement. The roughly 657 KB pending dataset remains browser-managed; source/evidence storage has not been replaced with a server cache. Browser rendering and network transfer remain additional costs. Multi-minute seasonal model fitting is separate from source-information updates.

Measurement evidence: `evidence/performance-2026-10-04/baseline.json` and `after.json`. Those runs used a labeled profiling declaration only; they did not alter the source workbook or establish actual reporting completeness.

Validation: 227 automated tests passed (10 existing Dash DataTable deprecation warnings). Desktop/mobile browser recovery passed with no page errors, including opening deferred checks without losing unsaved selections. Header screenshots inspected on desktop/mobile. Static checks passed. Native details toggle events are bridged to Dash explicitly so lazy loading works on actual browser expansion. Restarted the local dashboard with debug/reloader disabled.
