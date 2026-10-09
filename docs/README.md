# Documentation map

## Current documentation

- [Project setup and workflow](../README.md)
- [Weekly system and model contract](../WEEKLY_SYSTEM.md)
- [Architecture](../ARCHITECTURE.md)
- [Background forecast jobs and Vercel worker setup](FORECAST_JOBS.md)
- [Test results](../TEST_RESULTS.md)
- [Change history](../CHANGELOG.md)
- [Decision 90 authoritative specification](FINAL_WEEKLY_IMPLEMENTATION_SPEC.md)
- [Decision 90 integration and verification](DECISION90_IMPLEMENTATION_STATUS.md)
- [Earlier Revision 45 requirements](APPROVED_HANDOFF_REVISION45.md) (superseded where inconsistent)

## Historical records

`archive/` contains superseded handoffs, reconciliation reports, manuscript proposals, and per-change implementation reports. They are retained for traceability; current behavior is described by the documents above. `historical-pre-weekly/` preserves the previous monthly system documentation.

Model runs and verification artifacts remain in `../evidence/`. Original research sources remain in `../reconciliation/sources/`; earlier monthly PDF/conversion inputs are in `../reconciliation/historical-inputs/`.

## Repository cleanup — 5 October 2026

Moved 17 root-level historical Markdown files into `archive/` and relocated three historical input files. Removed the obsolete September 27 repository ZIP and checksum, plus disposable Python caches. Updated relative documentation links. Application code, test coverage, original evidence, and installed browser-test tools were preserved.

Local browser tools and runtime logs/PIDs are development artifacts, not production dependencies. They are excluded from Git or deployment packaging. Older monthly modules remain because regression tests still import them.

Verification after cleanup: 227 tests passed (10 existing Dash deprecation warnings); application import and health endpoint returned HTTP 200. Historical report generators were updated for relocated document paths.
