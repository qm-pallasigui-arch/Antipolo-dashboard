# SARIMANNAR residual search

`residual_search.py` is the offline tuning harness used to choose the weekly
SARIMA specification and the NNAR residual-model size for the hybrid model
shipped in `dashboard/weekly/`. It is a research tool: it runs outside the
Dash app, writes its own result files, and is **not** imported by the
application at runtime.

## Inputs

Each run is driven by a JSON config in this folder. The input CSVs are **not**
part of this repository — they live in a sibling `tradeoffanalysis/` project
next to this checkout, which is why the config paths are relative
(`../tradeoffanalysis/...`). Adjust the `path` field of a config to match your
own layout before running.

| File | Purpose |
|---|---|
| `residual_search_weekly.json`, `residual_search_weekly_wide.json` | Base weekly search configs (Dengue). |
| `rs_*.json` / `rs_*.md` | Full grid sweeps per disease. |
| `rt_*.json` / `rt_*_result.*` | Re-tuned runs against the final per-disease protocol. |
| `pin_*.json` / `pin_*_result.*` | Pinned configurations. The `pin_*` names are deliberate: the script writes results to `<config>_result.*`, so a config sharing that name overwrites its own input. |

## Running

```bash
python residual_search.py --config rs_dengue.json
```

Fitting a full grid is CPU-bound and slow — the `fast`/`full` tiers differ in
how many candidates and NNAR sizes are tried. Use the `pin_*` configs to
reproduce a specific settled result rather than re-running a sweep.

## Results

Each run writes `<config>_result.json`, `<config>_result.md` and a `.log`
alongside the config. The `.log` files are excluded from version control by the
repository `.gitignore`; the JSON and Markdown summaries are tracked as the
record of what was run and what it produced.

## Relationship to the app

The per-disease configurations these searches produced are recorded for the
application in `config/weekly_model_per_disease.json`. That file is what the
dashboard reads when `WEEKLY_MODEL_CONFIG` points at it.