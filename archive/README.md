# Historical archive

Everything under this directory is research or implementation provenance. None belongs to the current executable thesis system. Do not import archived modules into the application or seed historical outputs into live storage.

The finalized architecture is Prophet + XGBoost. [project-history-2026-11-05.zip](project-history-2026-11-05.zip) preserves 288 files, including 52 Markdown files, with their original paths relative to the repository root. It contains superseded documentation, the old changelog and handoffs, earlier implementations, audit inventories and one-time migration scripts. Every archived file was verified against its SHA-256 before its loose copy was removed. `ARCHIVE_MANIFEST.json` inside the ZIP lists those hashes.

To inspect or recover history, extract into a separate directory, not over the working project:

```powershell
Expand-Archive -LiteralPath archive/project-history-2026-11-05.zip -DestinationPath .artifacts/history-review
```

Original source paths and links are preserved as historical records; some refer to files outside the ZIP. Archived migration scripts can overwrite source or documentation and must not be run against the current project. Use a separate research environment if reproducing old implementations.

The [original model-development script and provenance](model_development/README.md) remain available separately. Archives are excluded from package discovery, default tests and Docker deployment.
