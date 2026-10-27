"""
Prototype forecasting inference ? PROTOTYPE ONLY

  * standalone Prophet, and
  * Prophet + optional residual correction

Usage (CLI):
    python icd_inference.py --block A00-A09
    python icd_inference.py --block B25-B34 --h 12 --learner lgbm
    python icd_inference.py --series series.json          # {"consultation_counts": [..]}
    python icd_inference.py --block A00-A09 --no-hybrid   # Prophet only
    python icd_inference.py --block A00-A09 --out f.json  # write JSON to file

Usage (import):
    from icd_inference import forecast_block, forecast_series
    out = forecast_block("A00-A09")          # reads the bundled CSV
    out = forecast_series([34, 26, 15, ...]) # pass the counts directly
"""

from __future__ import annotations

import argparse
import json
import logging

import numpy as np

import icd_forecast as F

# keep stderr clean for a web backend: Prophet/cmdstanpy chatty INFO logs
for _name in ("cmdstanpy", "prophet", "fbprophet", "stan"):
    logging.getLogger(_name).setLevel(logging.WARNING)

DEFAULT_LEARNER = "rf"
DEFAULT_H = 12


def _jsonable(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (tuple, list)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    return obj


def forecast_series(values, h=DEFAULT_H, learner=DEFAULT_LEARNER, do_hybrid=True):
    """Fit Prophet (and optionally the hybrid) on a flat count series.

    Parameters
    ----------
    values : sequence of numbers, monthly counts in chronological order.
    h      : forecast horizon in months.
    learner: residual corrector, one of F.ML_KEYS ("rf", "nnar", "lgbm", "svm").
    do_hybrid : set False to fit standalone Prophet only.

    Returns
    -------
    dict with keys: n_obs, h, prophet{forecast, params}, and optionally
    hybrid{learner, config, target, lags, lambda, abstained, correction,
    forecast, cv_mae, cv_mae_nocorr}, plus a note.
    """
    # TODO THESIS-METHOD:
    # This forecasting implementation is for prototype/dashboard integration only.
    # The final thesis forecasting algorithm, candidate models, evaluation design,
    # and model-selection rule are not yet approved.
    values = np.asarray(values, float)
    if values.ndim != 1 or len(values) < F.LAGS + 6:
        raise ValueError(f"need at least {F.LAGS + 6} monthly observations")

    params = F.tune_prophet(values)
    _, base_fc = F._prophet_fit(values, h, params)

    out = {
        "prototype": True,
        "n_obs": int(len(values)),
        "h": int(h),
        "prophet": {
            "forecast": [round(float(v), 2) for v in base_fc],
            "params": {k: v for k, v in params.items()},
        },
    }

    if not do_hybrid:
        return _jsonable(out)

    hybrid = {
        "learner": learner,
        "abstained": True,
        "lambda": 0.0,
        "correction": [0.0] * h,
        "forecast": [round(float(v), 2) for v in base_fc],
        "reason": None,
    }
    try:
        errs, meta = F.rolling_errors(values, params)
        sel = F.tune_hybrid(learner, errs)
        corr = F.ml_predict_seeds(learner, errs[sel["target"]], h, sel["config"],
                                  lags=sel["lags"], clip=False)
        corr = sel["lambda"] * np.asarray(corr, float)
        hybrid_fc = np.maximum(np.asarray(base_fc, float) + corr, 0.0)
        hybrid.update({
            "config": sel["config"],
            "target": sel["target"],
            "lags": sel["lags"],
            "lambda": sel["lambda"],
            "abstained": bool(sel["abstained"]),
            "correction": [round(float(v), 3) for v in corr],
            "forecast": [round(float(v), 2) for v in hybrid_fc],
            "cv_mae": round(float(sel["cv_mae"]), 3),
            "cv_mae_nocorr": round(float(sel["cv_mae_nocorr"]), 3),
            "roll": {k: int(v) for k, v in meta.items()},
        })
    except Exception as exc:  # noqa: BLE001  -> decline to correct on failure
        hybrid["reason"] = f"{type(exc).__name__}: {exc}"

    out["hybrid"] = hybrid
    out["note"] = "Prototype only; final thesis methodology is not approved."
    return _jsonable(out)


def forecast_block(code, variant="A", h=DEFAULT_H, learner=DEFAULT_LEARNER,
                   do_hybrid=True):
    """Read a block from the bundled CSV and forecast it."""
    if code not in F.BLOCKS:
        raise ValueError(f"unknown block {code!r}; available: {sorted(F.BLOCKS)}")
    df = F.block_frame(code, variant)
    return forecast_series(df["cases"].values.astype(float), h, learner, do_hybrid)


def _series_from_file(path):
    obj = json.load(open(path, encoding="utf-8"))
    if isinstance(obj, dict) and "consultation_counts" in obj:
        return np.asarray(obj["consultation_counts"], float)
    if isinstance(obj, dict) and "cases" in obj:
        return np.asarray(obj["cases"], float)
    if isinstance(obj, list):
        return np.asarray(obj, float)
    raise ValueError("series JSON must be a list of numbers or {\"cases\": [...]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--block", default=None,
                    help="ICD-10 block code (e.g. A00-A09) to read from the CSV")
    ap.add_argument("--series", default=None, help="path to a JSON series file")
    ap.add_argument("--h", type=int, default=DEFAULT_H)
    ap.add_argument("--learner", default=DEFAULT_LEARNER, choices=F.ML_KEYS)
    ap.add_argument("--no-hybrid", action="store_true")
    ap.add_argument("--out", default=None, help="write JSON to this file")
    args = ap.parse_args()

    if args.block is None and args.series is None:
        ap.error("one of --block or --series is required")
    if args.block:
        out = forecast_block(args.block, h=args.h, learner=args.learner,
                             do_hybrid=not args.no_hybrid)
        out["code"] = args.block
        out["category"] = F.BLOCKS[args.block]
    else:
        out = forecast_series(_series_from_file(args.series), h=args.h,
                              learner=args.learner,
                              do_hybrid=not args.no_hybrid)

    text = json.dumps(out, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
