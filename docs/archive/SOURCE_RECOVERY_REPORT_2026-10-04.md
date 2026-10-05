# Source-information confirmation recovery — 4 October 2026

Fixed a failed-confirmation state reset: returning the unchanged modal-open value triggered a form rebuild and cleared the user's unsaved source-information choices. Failed submissions now leave the pending dataset and modal state untouched and show an actionable error beside the confirmation controls. The active dataset remains unchanged.

Added a visible checking/applying status and disabled review action buttons while processing. Calendar conflicts now expose the actual validation reason. A browser regression verifies selecting completeness without a reference, seeing the error without losing the selection, entering the reference, and successfully confirming without reupload. Evidence requirements remain enforced.

Verification: 54 focused tests passed; six desktop/mobile Edge browser checks passed with no page errors; pyflakes passed. Error-state screenshot inspected. Evidence: `evidence/source-recovery-2026-10-04/results.json` and screenshots in that directory. Dashboard restarted with debug/reloader disabled.

## Review hierarchy — 4 October 2026

Organized the modal into numbered worksheet, source-information, and read-only checks/eligibility sections, followed by one final action area. Removed Review Details and moved all checks ahead of confirmation. Research eligibility is a status within the checks section rather than a separate ambiguous dropdown. Source fields are visible, with a responsive two-column desktop layout. Apply Worksheet Changes and Apply Source Information are secondary actions; Confirm & Use Data is the sole primary action, with an explicit description of activation versus cancellation. History-only review hides the final-confirmation explanation.

Verification: 54 focused tests passed; 14 existing workflow browser checks and 6 source-recovery checks passed with no page errors. The recovery browser also asserts numbered sections, absence of Review Details, and checks before final actions. Desktop screenshot inspected; mobile recovery and overflow checks passed. Static checks passed.
