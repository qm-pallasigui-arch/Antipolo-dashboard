# Repository hygiene

Commit application code, test code, dependency pins, documentation, required test fixtures and source provenance. File extensions alone do not determine whether something is disposable: configuration and fixtures may require JSON, while performance-result JSON is generated output.

Routine browser screenshots now go to `.artifacts/browser-monthly/`. Performance screenshots go to `.artifacts/performance/`. These directories are ignored by Git and Docker and reuse stable filenames. The performance test prints measurements by default; saving JSON is optional:

```powershell
.venv\Scripts\python.exe tests/browser_monthly_performance.py .artifacts/performance/results.json
```

Historical `evidence/` files referenced by research documentation remain tracked. Do not delete all evidence, all JSON, or all images. Keep only deliberately selected evidence for a release or thesis milestone; routine reruns belong in `.artifacts/`.

Preview safe cleanup, then apply it:

```powershell
powershell -NoProfile -File tools/clean_generated.ps1
powershell -NoProfile -File tools/clean_generated.ps1 -Apply
```

The cleaner checks paths, refuses tracked files and linked directories, and removes only known test scratch folders, Python caches in source/test/tool directories, pytest caches and `.artifacts/`. It preserves `.monthly/` (active data and accounts), `.venv/`, `.git/`, source datasets, model/job state, archives and historical evidence. Stop test runs before cleaning their temporary output. If Windows denies access, retry with the permissions used to create those test folders; do not reset permissions across the repository.

Review `git diff --cached --name-only` before committing. `.gitignore` prevents new files from being added by default; it does not untrack files already committed or shrink Git history. Removing old committed binaries from history is a separate coordinated task, not routine cleanup. Never use an unrestricted `git clean -fdx`: it can delete the environment, local database and secrets.
