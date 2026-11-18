# Project instructions

## Project context
- Antipolo monthly ICD-10 consultation dashboard for ages 5–19.
- Stack: Python, Dash, Flask, Plotly, pandas, Prophet and XGBoost.
- Local persistence: SQLite. Configured cloud persistence: PostgreSQL/Supabase.
- Administrators upload and activate datasets and generate forecasts.
- Viewers inspect results and export reports.
- Read README.md and docs/README.md before changing project behavior.

## Working approach
- Inspect existing code and current changes before editing.
- Preserve unrelated work and existing staged changes.
- For new screens or substantial workflow changes, present a brief
  proposal and ask about requirements not already established.
- Routine fixes may proceed within the requested scope.
- In plan mode, inspect and propose; do not edit files.
- Ask before adding dependencies or changing model methodology.

## UI and accessibility
- Reuse dashboard/monthly/components.py and existing chart helpers.
- Follow dashboard/assets/monthly.css and documented design conventions.
- Keep interface styling in CSS and chart styling in shared Plotly
  configuration; retain framework-required dynamic visibility controls.
- Preserve the established navy and teal visual language.
- Provide clear loading, success, error, empty and disabled states.
- Prevent duplicate forecast submissions while processing.
- Show real progress when available; never invent percentages.
- Keep labels visible, controls keyboard accessible and focus clear.
- Support mobile layouts, readable contrast and reduced motion.
- Do not convey meaning through color alone.
- Explain significant design choices and verification performed.

## UI/UX principles
Every UI choice must trace to a named principle below. Target: WCAG 2.2 AA.

### Design interview (new screens, components or workflow changes)
Before substantial UI or workflow changes, review all seven topics:
(1) user and task, (2) primary action, (3) content and data, (4) states,
(5) device context, (6) accessibility needs, (7) existing components to reuse.
Reuse answers established in the project or conversation and briefly state
relevant assumptions. Ask only unresolved questions, in one numbered batch.
Wait for answers that materially affect implementation; do not repeat the
interview when all relevant requirements are already established.
- "Trivial" means a copy fix, token swap, or bug fix with no visual or
  workflow change. When skipping, say "Skipping interview: trivial edit."
- Pushback-then-confirm: if a requested design conflicts with a principle
  here, state the conflict once, briefly, then ask for explicit
  confirmation before following the owner's choice.

### Principles, applied to this dashboard
- Visual hierarchy: give each task area a clear primary action; the headline result
  (e.g. historical Top Five) is visually dominant over secondary detail.
- Hick's Law: prioritize and group secondary actions. Use disclosure or
  overflow menus when they reduce demonstrated clutter, not solely
  because an item count exceeds a fixed number.
- Miller's Law: group KPIs, filters and table columns into small labeled
  chunks. Treat item counts as guidelines, not hard limits; preserve
  useful comparisons and access to all seven study groups.
- Gestalt (proximity, common region): group with spacing and background
  before adding borders.
- Progressive disclosure: advanced model details and diagnostics stay
  collapsed until requested.
- Doherty threshold: if a response takes more than roughly 400ms, show a
  skeleton or progress state; forecast runs show real status per the
  rules above.
- Control and recovery: destructive or state-changing admin actions
  (dataset activation, deletion, forecast re-run) need confirmation or
  undo, and a visible cancel.
- Nielsen's heuristics (especially system status, error prevention,
  recognition over recall): show the active dataset, applied filters and
  latest model attempt status on screen.
- Jakob's Law: use familiar patterns for tables, tabs, filters and
  exports unless there is a stated reason not to.
- Feedback: every action gives visible confirmation, success or failure.
- Forms: visible labels; validate on blur; error messages state what
  happened and how to fix it; action-specific button labels
  ("Upload dataset", not "Submit").

### Accessibility specifics
- Contrast: 4.5:1 for body text, 3:1 for large text and UI components,
  including chart text and series colors against their backgrounds.
- Every interactive element has a visible :focus-visible style and is
  keyboard operable with logical order.
- Semantic HTML first; ARIA only when no native element fits; icon-only
  controls have accessible names.
- Touch targets at least 44px recommended (verify the exact WCAG 2.2
  target-size criterion before citing it).
- Charts: provide a table or text alternative for key results; do not
  rely on color alone to distinguish series.
- Respect prefers-reduced-motion.

### Prohibitions
- No generic "AI slop": default purple/blue gradients, centered
  hero-plus-three-cards layouts, meaningless glassmorphism, emoji as
  icons, placeholder-feeling copy, unmotivated shadows or rounded corners.
- Use existing CSS tokens for interface styling and shared Plotly theme
  configuration for charts. Centralize reusable chart colors and
  typography in the chart helpers; keep them consistent with the interface.
- Avoid new hard-coded visual values in individual views. If the existing
  design system is insufficient, propose additions and ask before applying.
- No new component when a suitable one exists.
- No building non-trivial UI while material requirements remain unanswered.
- No code in plan mode.

### Self-review before declaring UI work done
- [ ] Relevant interview topics covered using established answers or clarification; trivial skip stated when applicable
- [ ] Each design choice maps to a named principle
- [ ] Loading, success, error, empty and disabled states handled
- [ ] Contrast, focus, keyboard and reduced-motion checked
- [ ] Existing CSS tokens, shared chart configuration and components reused; additions approved
- [ ] Pushbacks raised and confirmed by the owner

## Data and forecasting
- Preserve original uploads and canonical source observations.
- Explicit zero is valid data; unavailable values remain unknown.
- Preserve actual calendar dates and reporting gaps.
- Attempt modeling for all seven candidate ICD-10 blocks.
- Reporting coverage describes data; it does not exclude candidates.
- Prophet is the base model; XGBoost supplies residual corrections.
- Do not silently substitute models or fabricate successful results.
- Keep prototype results clearly labeled as provisional.
- Do not change parameters, evaluation splits or gap handling without
  explicit authorization.
- Display the latest compatible model attempt, including failure.
- Keep historical Top Five separate from projected rankings.
- Enforce permissions on the server.

## Local execution and troubleshooting
- Use the existing .venv; do not recreate it unnecessarily.
- Start locally with run.bat or .venv\Scripts\python.exe app.py.
- Verify http://127.0.0.1:8050/healthz after startup.
- Check existing processes before starting another server.
- For stalled forecasts, inspect logs, saved run status and temporary
  folder permissions before changing model settings.
- Prophet/CmdStan requires writable temporary files.
- Follow permission controls; do not reset repository-wide permissions.
- Stop only processes identified as belonging to this project.

## Verification
- Run checks appropriate to the changed behavior.
- Use isolated test databases; do not use active accounts or datasets
  as disposable test fixtures.
- Run relevant pytest tests for application changes.
- Run tests/browser_monthly.py for substantial UI or callback changes.
- Use tools/verify_prototype.py when real model execution needs checking.
- Check documentation links and git diff --check for documentation edits.
- Report what passed, what failed and what was not verified.
- Never present historical test evidence as a fresh verification.

## Repository hygiene
- Keep current guidance in existing documents; avoid duplicate reports.
- Put routine logs, screenshots and generated audits in .artifacts/.
- Preserve .monthly/, source datasets, research provenance and archives.
- Do not import or execute archived migration code in the live project.
- Verify recoverable archives before removing original files.
- Never use unrestricted git clean -fdx.
- Do not stage, commit, push or deploy unless requested.

## Completion report
- State what changed and why.
- Summarize verification and remaining limitations.
- For UI work, briefly identify reused components and design rationale.
- For UI work, end with a short Design Rationale: the 2-4 principles
  applied and why, plus any open questions (or "none").
