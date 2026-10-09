# -*- coding: utf-8 -*-
"""residual_search.py - SARIMA + NNAR residual-hybrid search, dataset-agnostic.

PURPOSE
Finds a SARIMA specification whose residuals a neural residual model (NNAR) can
actually exploit, and reports whether that translates into better forecasts.

Motivation. Conventional SARIMA selection requires Ljung-Box-PASSING residuals
(white noise). That is self-defeating for a residual hybrid: by construction
there is nothing left for the residual model to learn. This script inverts the
filter (default `residual_filter: "non_white"`) so it searches for candidates
that DO leave structure, then optimises the residual model on them and measures
the real consequence.

PIPELINE
  1. load      - read, validate, impute, profile date gaps
  2. split     - train / test by count or date
  3. stage 1   - SARIMA grid on TRAIN ONLY: AIC, Ljung-Box, convergence
  4. filter    - keep candidates matching residual_filter (default non-white)
  5. shortlist - top N by AIC
  6. stage 2   - NNAR validation search per shortlisted candidate; rank by
                 hybrid VALIDATION RMSE
  7. evaluate  - refit winner on full train; forecast at each horizon; score
                 RMSE / MAE / MAPE against the SARIMA baseline and a
                 seasonal-naive reference; Diebold-Mariano significance test;
                 stratum split where n >= 20
  8. emit      - JSON (dashboard), markdown report, two charts

DISCIPLINE
  - The test set is touched exactly once, in stage 7, after selection is locked.
  - Stage 1 and stage 2 use training data only.
  - Positional (not calendar) indexing throughout, so irregular reporting gaps
    do not break the seasonal alignment; the gap profile is reported.
  - Model-fit errors are surfaced, never silently swallowed: a candidate that
    fails records its reason, and an empty stage raises with the cause.

USAGE
  python residual_search.py --config dengue_weekly.json
  python residual_search.py --data weekly_dengue.csv --seasonal 52 --train-n 468

Main-guard required (multiprocessing safety).
"""
import argparse
import itertools
import json
import os
import sys
import time
import traceback
import warnings

warnings.filterwarnings("ignore")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
# Parallelism is at PROCESS level (Pool), so BLAS must stay single-threaded or the
# workers oversubscribe the cores and run slower than serial. Set before numpy import
# so spawned Windows workers pick it up too.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "1")

import multiprocessing as mp

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.stattools import adfuller, kpss
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

T0 = time.time()


def log(msg):
    print(f"[{time.time()-T0:7.1f}s] {msg}", flush=True)


# ----------------------------------------------------------------- config
DEFAULT_CONFIG = {
    "data": {"path": None, "date_col": "date", "value_col": "cases",
             "frequency": "weekly"},
    "split": {"mode": "count", "train_n": 468, "test_start": None},
    "imputation": {"rule": "zero_to_half", "value": 0.5},
    "seasonal": {"period": 52, "inferred_by": "config", "auto_max": 60,
                 "acf_min_lag": 4, "acf_min_peak": 0.20},
    "sarima": {"p": [0, 1, 2], "d": [0, 1], "q": [0, 1, 2],
               "P": [0, 1], "D": [1], "Q": [0], "maxiter": 300},
    "grid_tier": "fast",
    "n_jobs": 0,
    "selection": {"residual_filter": "non_white", "lb_alpha": 0.05,
                  "rank_by": "hybrid_val_rmse", "candidates_to_refine": 4},
    "nnar": {"lags": [6, 12], "hidden": [2, 5], "validation_n": 52,
             "validation_windows": 3, "window_aggregate": "mean",
             "max_iter": 2000, "random_state": 42},
    "evaluation": {"horizons": [4, 13, 26, 52], "metrics": ["RMSE", "MAE", "MAPE"],
                   "stratum_min_n": 20, "stratum_threshold": 70,
                   "dm_alpha": 0.05},
    "output": {"json": "results.json", "report": "report.md",
               "chart_horizons": "forecast_by_horizon.png",
               "chart_error": "error_by_horizon.png"},
}


# Grid tiers. Individual 52-week seasonal fits cost 0.1s-70s (measured), so grid
# width is the whole runtime story. Each tier is a documented BOUNDED search, not
# an exhaustive one, and the tier actually used is printed in the report.
#   fast      16 candidates  ~100-115s on 12 cores  (2-minute budget)
#   standard  32 candidates  ~200s
#   full     108 candidates  ~1400s
# All three contain (2,0,0)(2,1,1,52) on 52-week data.
GRID_TIERS = {
    "fast":     {"p": [1, 2],       "d": [0, 1], "q": [0],    "P": [1, 2],
                 "D": [1],          "Q": [0, 1]},
    "standard": {"p": [1, 2],       "d": [0, 1], "q": [0, 1], "P": [1, 2],
                 "D": [1],          "Q": [0, 1]},
    "full":     {"p": [0, 1, 2],    "d": [0, 1], "q": [0, 1, 2], "P": [0, 1, 2],
                 "D": [1],          "Q": [0, 1]},
}
TIER_NOTES = {
    "fast": "Excludes q>0, p=0, p=3. On dengue this forgoes the q sweep, where MAPE "
            "improved monotonically with q (23.11 at q=0 to 21.98 at q=3).",
    "standard": "Excludes q>1, p=0, p=3, P=0, D=0.",
    "full": "Excludes p>2, q>2, P>2, Q=2, D=0.",
}


def merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        else:
            out[k] = v
    return out


# ----------------------------------------------------------------- data
def acorr(x, nlags):
    out = np.empty(nlags + 1)
    out[0] = 1.0
    x = np.asarray(x, float)
    x = x - x.mean()
    denom = float(np.dot(x, x))
    for i in range(1, nlags + 1):
        out[i] = float(np.dot(x[i:], x[:-i])) / denom if denom > 0 else 0.0
    return out


def load_series(cfg):
    d = cfg["data"]
    path = d["path"]
    if not path:
        raise SystemExit("config.data.path is required")
    raw = pd.read_csv(path)
    if d["date_col"] not in raw.columns:
        raise SystemExit(f"date column {d['date_col']!r} not found in {path}")
    val_col = d["value_col"] if d["value_col"] in raw.columns else raw.columns[-1]
    dates = pd.to_datetime(raw[d["date_col"]])
    values = pd.to_numeric(raw[val_col], errors="coerce")

    prof = {"value_column_used": val_col, "n_rows": int(len(raw)),
            "nulls_before": int(values.isna().sum())}

    imp = cfg["imputation"]
    zeros = int((values == 0).sum())
    if imp["rule"] == "zero_to_half":
        values = values.replace(0, imp["value"])
    elif imp["rule"] == "drop":
        values = values.replace(0, np.nan)
    elif imp["rule"] != "none":
        raise SystemExit(f"unknown imputation.rule {imp['rule']!r} "
                         f"(expected zero_to_half, drop or none)")
    prof["zeros_found"] = zeros
    prof["imputation_rule"] = imp["rule"]
    prof["nulls_after_imputation"] = int(values.isna().sum())

    gaps = dates.diff().dt.days.dropna().value_counts().sort_index()
    prof["gap_profile_days"] = {str(int(k)): int(v) for k, v in gaps.items()}
    prof["span_days"] = int((dates.max() - dates.min()).days)
    try:
        prof["inferred_freq"] = pd.infer_freq(pd.DatetimeIndex(dates))
    except Exception:
        prof["inferred_freq"] = None
    prof["mean_gap_days"] = round(float(gaps.mean()), 3) if len(gaps) else None

    series = pd.Series(values.values.astype(float),
                       index=pd.DatetimeIndex(dates), name=val_col).dropna()
    # Positional (not calendar) indexing is used throughout, so an interior gap
    # silently shortens the series and shifts every later seasonal position by
    # one. That misaligns a period-52 fit, so it is reported loudly rather than
    # left for the caller to infer from `n_rows`.
    dropped = int(len(values) - len(series))
    prof["rows_dropped_as_null"] = dropped
    if dropped:
        log(f"WARNING: dropped {dropped} null observation(s); positional indexing "
            f"means the seasonal alignment after each gap is shifted. Treat the "
            f"selected specification as provisional and re-validate it against a "
            f"null-preserving fit before relying on it.")
    return series, prof


def infer_seasonal(series, cfg):
    s = cfg["seasonal"]
    if s.get("period") not in (None, "auto"):
        return int(s["period"]), "config"
    n = min(len(series) - 1, int(s.get("auto_max", 60)))
    if n < 4:
        return 1, "fallback_default"
    a = acorr(series.values, n)
    lo = int(s.get("acf_min_lag", 4))
    if lo >= len(a):
        return 1, "acf_below_min_lag"
    k = int(np.nanargmax(a[lo:])) + lo
    peak = float(a[k])
    return (k, "acf") if peak >= float(s.get("acf_min_peak", 0.2)) else (1, "acf_no_clear_peak")


def make_split(series, cfg):
    sp = cfg["split"]
    if sp.get("mode") == "date" and sp.get("test_start"):
        cut = pd.Timestamp(sp["test_start"])
        train, test = series[series.index < cut], series[series.index >= cut]
    else:
        n = int(sp["train_n"])
        train, test = series.iloc[:n], series.iloc[n:]
    if len(test) == 0:
        raise SystemExit("split produced an empty test set")
    return train, test


def diagnose(train, cfg):
    res = {}
    x = np.asarray(train, float)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res["adf_raw"] = round(float(adfuller(x)[1]), 6)
    except Exception as e:
        res["adf_raw"] = f"failed: {e}"
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res["kpss_raw"] = round(float(kpss(x, regression="c")[1]), 6)
    except Exception as e:
        res["kpss_raw"] = f"failed: {e}"
    a = res.get("adf_raw")
    res["suggested_d"] = 1 if (isinstance(a, float) and a > 0.05) else 0
    res["searched_d"] = cfg["sarima"]["d"]
    res["searched_D"] = cfg["sarima"]["D"]
    return res


# ----------------------------------------------------------------- metrics
def metrics(y, p):
    yt = np.asarray(y, float)
    yp = np.asarray(p, float)
    e = yp - yt
    rmse = float(np.sqrt(mean_squared_error(yt, yp)))
    mae = float(mean_absolute_error(yt, yp))
    m = yt != 0
    n_zero = int((~m).sum())
    mape = float(np.mean(np.abs(e[m] / yt[m])) * 100) if m.any() else float("nan")
    return {"RMSE": rmse, "MAE": mae, "MAPE": mape, "zero_actuals_excluded": n_zero}


def improvement_pct(m, base):
    out = {}
    for k in ("RMSE", "MAE", "MAPE"):
        if base.get(k) and np.isfinite(m[k]) and np.isfinite(base[k]):
            out[k] = float(100.0 * (m[k] - base[k]) / base[k])
    return out


def dm_test(loss_a, loss_b, alpha=0.05):
    """Diebold-Mariano on loss differentials. Negative differential favours candidate."""
    d = np.asarray(loss_a, float) - np.asarray(loss_b, float)
    d = d[np.isfinite(d)]
    n = len(d)
    if n < 3:
        return {"n": n, "significant": False, "note": "too few periods for a test"}
    dbar = float(d.mean())
    s2 = float(np.var(d, ddof=1)) / n
    dm_naive = dbar / np.sqrt(s2) if s2 > 0 else 0.0
    p_naive = float(2 * (1 - stats.norm.cdf(abs(dm_naive))))
    gamma = 0.0
    for j in range(1, min(n, 10)):
        if n - j > 2:
            g = float(np.corrcoef(d[j:], d[:-j])[0, 1])
            if np.isfinite(g):
                gamma += g
    denom = s2 * (1.0 + 2.0 * sum((n - j) / n * gamma for j in range(1, min(n, 10))))
    dm_hln = dbar / np.sqrt(denom) if denom > 0 else 0.0
    p_hln = float(2 * (1 - stats.norm.cdf(abs(dm_hln))))
    return {"n": n, "mean_loss_differential": round(dbar, 4),
            "dm_statistic": round(dm_hln, 4), "p_value": round(p_hln, 4),
            "dm_statistic_naive": round(dm_naive, 4), "p_value_naive": round(p_naive, 4),
            "significant": bool(p_hln < alpha), "alpha": alpha,
            "note": ("negative differential favours the hybrid"
                     if dbar < 0 else "positive differential favours the baseline")}


# ----------------------------------------------------------------- NNAR
def sup(vals, lag):
    v = np.asarray(vals, float)
    X, y = [], []
    for i in range(lag, len(v)):
        X.append(v[i - lag:i])
        y.append(v[i])
    return np.array(X), np.array(y)


def recurse(pf, hist, lag, steps):
    h = list(np.asarray(hist, float))
    out = []
    for _ in range(steps):
        out.append(float(pf(np.asarray(h[-lag:]).reshape(1, -1))[0]))
        h.append(out[-1])
    return np.array(out)


def fit_nnar(series, lag, k, cfg):
    v = np.asarray(series, float)
    X, y = sup(v, lag)
    sc = StandardScaler()
    sc.fit(v.reshape(-1, 1))
    Xs = np.array([sc.transform(r.reshape(-1, 1)).flatten() for r in X])
    ys = sc.transform(y.reshape(-1, 1)).flatten()
    m = MLPRegressor(hidden_layer_sizes=(k,), activation="relu", solver="adam",
                     max_iter=int(cfg["nnar"]["max_iter"]),
                     random_state=int(cfg["nnar"]["random_state"])).fit(Xs, ys)

    def predict(rows):
        arr = np.array([sc.transform(np.asarray(r, float).reshape(-1, 1)).flatten()
                        for r in rows])
        if arr.ndim == 1:                       # single row passed flat
            arr = arr.reshape(1, -1)
        # inverse_transform requires 2D (n_samples, n_features)
        return sc.inverse_transform(np.asarray(m.predict(arr), float).reshape(-1, 1)).ravel()
    return predict


# ----------------------------------------------------------------- stage 1
def fit_one(job):
    """Worker: fit one SARIMA on the FULL train set.

    Returns residuals AND the horizon forecast, so stage 2 and the final
    evaluation never have to refit. Must stay top-level for Windows spawn.
    """
    vals, order, seasonal, maxiter, lb_lags, alpha, H = job
    rec = {"order": list(order), "seasonal": list(seasonal)}
    try:
        f = SARIMAX(np.asarray(vals, float), order=tuple(order),
                    seasonal_order=tuple(seasonal), trend=None,
                    enforce_stationarity=False,
                    enforce_invertibility=False).fit(disp=False, maxiter=int(maxiter))
        resid = np.asarray(f.resid, float)
        if not np.isfinite(f.aic) or np.nanstd(resid) < 1e-6:
            rec.update({"aic": None, "error": "degenerate residuals"})
            return rec
        lb = acorr_ljungbox(pd.Series(resid).dropna(), lags=lb_lags, return_df=True)
        pv = {str(int(k)): float(v) for k, v in zip(lb_lags, lb["lb_pvalue"])}
        fc = np.asarray(f.get_forecast(steps=H).predicted_mean, float)
        rec.update({"aic": float(f.aic), "lb_p": pv,
                    "white_noise": all(v > alpha for v in pv.values()),
                    "converged": bool(f.mle_retvals.get("converged", True)),
                    "_resid": resid.tolist(), "_fc": fc.tolist()})
    except Exception as ex:
        rec.update({"aic": None, "lb_p": None, "white_noise": None,
                    "converged": False, "error": f"{type(ex).__name__}: {ex}"})
    return rec


def fit_baseline_one(job):
    """Worker: fit on train[:-nval] and forecast the held-back validation block."""
    vals, order, seasonal, maxiter, nval = job
    try:
        f = SARIMAX(np.asarray(vals, float), order=tuple(order),
                    seasonal_order=tuple(seasonal), trend=None,
                    enforce_stationarity=False,
                    enforce_invertibility=False).fit(disp=False, maxiter=int(maxiter))
        fc = np.asarray(f.get_forecast(steps=nval).predicted_mean, float)
        return {"_base_val": fc.tolist()}
    except Exception as ex:
        return {"_base_val": None, "error": f"{type(ex).__name__}: {ex}"}


def _run_pool(fn, jobs, n_jobs, label):
    """Map fn over jobs, in parallel when n_jobs > 1. Falls back to serial."""
    if n_jobs <= 1 or len(jobs) <= 1:
        return [fn(j) for j in jobs]
    ctx = mp.get_context("spawn")
    t0 = time.time()
    with ctx.Pool(processes=min(n_jobs, len(jobs))) as pool:
        out = []
        for i, r in enumerate(pool.imap_unordered(fn, jobs), 1):
            out.append(r)
            log(f"  {label} {i}/{len(jobs)} ({time.time()-t0:.0f}s elapsed)")
    return out


def stage1_grid(train, cfg, period, n_jobs):
    g = cfg["sarima"]
    grid = list(itertools.product(g["p"], g["d"], g["q"], g["P"], g["D"], g["Q"]))
    sel = cfg["selection"]
    lb_lags = [period, 2 * period] if period > 1 else [1, 2]
    H = max(cfg["evaluation"]["horizons"])
    log(f"stage 1: {len(grid)} candidates, train n={len(train)}, LB lags {lb_lags}, "
        f"{n_jobs} worker(s)")
    jobs = [(train.values.tolist(), (p, d, q), (P, D, Q, period),
             g["maxiter"], lb_lags, sel["lb_alpha"], H)
            for (p, d, q, P, D, Q) in grid]
    # Grid order is left as-is: sorting heaviest-first was tried and measured SLOWER
    # (140s vs 130s), because the expensive candidates are of similar cost, so
    # interleaving lets cheap ones clear slots early for the heavy ones.
    out = _run_pool(fit_one, jobs, n_jobs, "stage 1")
    out.sort(key=lambda r: (r.get("aic") is None, r.get("aic") or 0.0))
    rejected = sum(1 for r in out if r.get("aic") is None)
    return out, rejected


def stage1_filter(cands, cfg):
    mode = cfg["selection"]["residual_filter"]
    if mode == "any":
        keep = lambda c: c.get("aic") is not None
    elif mode == "white":
        keep = lambda c: c.get("white_noise") is True
    else:
        keep = lambda c: c.get("white_noise") is False
    return [c for c in cands if keep(c) and c.get("converged")], mode


# ----------------------------------------------------------------- stage 2
def nnar_search(resid, cfg):
    nval = int(cfg["nnar"]["validation_n"])
    tr_fit, tr_val = resid[:-nval], resid[-nval:]
    best, errors = None, []
    for lag in cfg["nnar"]["lags"]:
        for k in cfg["nnar"]["hidden"]:
            try:
                pf = fit_nnar(tr_fit, lag, k, cfg)
                v = float(np.sqrt(mean_squared_error(tr_val, recurse(pf, tr_fit, lag, nval))))
                if best is None or v < best[0]:
                    best = (v, int(lag), int(k))
            except Exception as ex:
                errors.append(f"lag={lag} k={k}: {type(ex).__name__}: {ex}")
    if best is None:
        raise RuntimeError("NNAR search produced no candidate. First errors: "
                           + " | ".join(errors[:3]))
    return best


def sarima_fit(train_values, order, seasonal, cfg):
    return SARIMAX(train_values, order=order, seasonal_order=seasonal, trend=None,
                   enforce_stationarity=False,
                   enforce_invertibility=False).fit(disp=False, maxiter=int(cfg["sarima"]["maxiter"]))


def _window_score(vals, how):
    return float(np.mean(vals)) if how == "mean" else float(np.max(vals))


def stage2(shortlist, train, cfg, n_jobs):
    """NNAR optimisation on cached stage-1 residuals.

    The full SARIMA fit is NOT repeated: stage 1 already returned residuals and the
    horizon forecast. Only the held-back validation baseline is fitted here, and
    those fits run in parallel.
    """
    rows = []
    nval = int(cfg["nnar"]["validation_n"])
    K = max(1, int(cfg["nnar"].get("validation_windows", 1)))
    agg = cfg["nnar"].get("window_aggregate", "mean")
    tvals = train.values

    # Multiple held-back windows. A single 52-week block is ONE calendar year, and
    # with ~9 years of weekly history any single block is arbitrary; on dengue the
    # only single available block (2024) is atypical, so selecting on it rewards
    # models that fit an anomaly. Per-window detail is still reported, so an
    # outlier window stays visible instead of being hidden by the aggregate.
    windows = []
    for i in range(K):
        end = len(tvals) - i * nval
        start = end - nval
        if start < 2 * nval:                 # keep enough history for a seasonal fit
            break
        windows.append((start, end))
    if not windows:
        windows = [(len(tvals) - nval, len(tvals))]
    wlbl = ", ".join(f"{train.index[s].date()}..{train.index[e-1].date()}"
                     for s, e in windows)
    log(f"stage 2: {len(shortlist)} candidates x {len(windows)} validation windows "
        f"({wlbl}), aggregated by {agg}")

    jobs, meta = [], []
    for ci, c in enumerate(shortlist):
        for wi, (s, e) in enumerate(windows):
            jobs.append((tvals[:s].tolist(), tuple(c["order"]), tuple(c["seasonal"]),
                         cfg["sarima"]["maxiter"], nval))
            meta.append((ci, wi))
    fits = _run_pool(fit_baseline_one, jobs, n_jobs, "stage 2 fits")
    base_by = {}
    for (ci, wi), r in zip(meta, fits):
        base_by[(ci, wi)] = (np.asarray(r["_base_val"], float)
                             if r.get("_base_val") else None)

    for ci, c in enumerate(shortlist):
        rec = dict(c)
        try:
            resid = np.asarray(c["_resid"], float)
            per_cfg = {}
            for lag in cfg["nnar"]["lags"]:
                for k in cfg["nnar"]["hidden"]:
                    errs = []
                    for wi, (s, e) in enumerate(windows):
                        bv = base_by.get((ci, wi))
                        if bv is None or not np.isfinite(bv).all():
                            raise ValueError(f"validation fit failed for window {wi}")
                        tr_fit, tr_val = resid[:s], resid[s:e]
                        pf = fit_nnar(tr_fit, lag, k, cfg)
                        errs.append(float(np.sqrt(mean_squared_error(
                            tr_val, bv + recurse(pf, tr_fit, lag, e - s)))))
                    per_cfg[(int(lag), int(k))] = errs
            if not per_cfg:
                raise RuntimeError("no NNAR configuration could be evaluated")
            lag, k = min(per_cfg, key=lambda kk: _window_score(per_cfg[kk], agg))

            base_err, nnar_err, hyb_err = [], [], []
            for wi, (s, e) in enumerate(windows):
                bv = base_by.get((ci, wi))
                if bv is None:
                    raise RuntimeError(
                        f"no baseline fit for candidate {ci} validation window {wi}; "
                        f"the stage 2 fit pool returned an incomplete result")
                tr_fit, tr_val = resid[:s], resid[s:e]
                pf = fit_nnar(tr_fit, lag, k, cfg)
                path = recurse(pf, tr_fit, lag, e - s)
                base_err.append(float(np.sqrt(mean_squared_error(tr_val, bv))))
                nnar_err.append(float(np.sqrt(mean_squared_error(tr_val, path))))
                hyb_err.append(float(np.sqrt(mean_squared_error(tr_val, bv + path))))

            hb, bb, nb = (_window_score(hyb_err, agg), _window_score(base_err, agg),
                          _window_score(nnar_err, agg))
            rec.update({
                "nnar": {"lag": lag, "k": k},
                "hybrid_val_rmse": hb, "baseline_val_rmse": bb, "nnar_val_rmse": nb,
                "nnar_helps_baseline": bool(nb < bb),
                "per_window": {"hybrid": hyb_err, "baseline": base_err, "nnar": nnar_err,
                               "window": [f"{train.index[s].date()}..{train.index[e-1].date()}"
                                          for s, e in windows]},
                "improvement_pct": (float(100 * (hb - bb) / bb) if bb else None)})
        except Exception as ex:
            rec.update({"nnar": None, "error": f"{type(ex).__name__}: {ex}"})
        rows.append(rec)
    return rows


# ----------------------------------------------------------------- evaluate
def build_winner(train, winner, cfg):
    order, seasonal = tuple(winner["order"]), tuple(winner["seasonal"])
    lag, k = winner["nnar"]["lag"], winner["nnar"]["k"]
    H = max(cfg["evaluation"]["horizons"])
    # residuals and the H-step forecast both come from stage 1 - no refit here
    resid = np.asarray(winner["_resid"], float)
    base_fc = np.asarray(winner["_fc"], float)[:H]
    pf = fit_nnar(resid, lag, k, cfg)
    hyb_fc = np.maximum(base_fc + recurse(pf, resid, lag, H), 0.0)
    period = int(seasonal[3])
    naive = np.array([train.values[i - period] if (i - period) >= 0 else np.nan
                      for i in range(len(train), len(train) + H)], float)
    return base_fc, hyb_fc, naive, resid


def evaluate(test, base_fc, hyb_fc, naive, cfg, dates_test):
    rows = []
    min_n = int(cfg["evaluation"]["stratum_min_n"])
    thr = float(cfg["evaluation"]["stratum_threshold"])
    alpha = float(cfg["evaluation"]["dm_alpha"])
    for h in cfg["evaluation"]["horizons"]:
        h = int(h)
        if h > len(test):
            log(f"  horizon {h} exceeds test length {len(test)} - skipped")
            continue
        y = np.asarray(test.values[:h], float)
        b, hy, nv = base_fc[:h], hyb_fc[:h], naive[:h]
        m_hyb, m_base = metrics(y, hy), metrics(y, b)
        m_nv = metrics(y, nv) if np.isfinite(nv).all() else None
        rec = {"h": h, "n": h,
               "dates": [str(d.date()) for d in dates_test[:h]],
               "actual": [round(float(x), 3) for x in y],
               "sarima": [round(float(x), 3) for x in b],
               "hybrid": [round(float(x), 3) for x in hy],
               "seasonal_naive": [round(float(x), 3) for x in nv] if m_nv else None,
               "metrics": {"hybrid": m_hyb, "baseline": m_base, "seasonal_naive": m_nv},
               "improvement_pct": improvement_pct(m_hyb, m_base),
               "dm_test": dm_test(np.abs(hy - y), np.abs(b - y), alpha)}
        if h >= min_n:
            low = y < thr
            rec["strata"] = {}
            for name, mask in (("low", low), ("high", ~low)):
                if int(mask.sum()) >= 3:
                    rec["strata"][name] = {"n": int(mask.sum()),
                                           "hybrid": metrics(y[mask], hy[mask]),
                                           "baseline": metrics(y[mask], b[mask])}
        rows.append(rec)
        log(f"  horizon {h:3d}: base RMSE {m_base['RMSE']:7.2f} MAPE {m_base['MAPE']:6.2f}% | "
            f"hybrid RMSE {m_hyb['RMSE']:7.2f} MAPE {m_hyb['MAPE']:6.2f}% | "
            f"DM p={rec['dm_test'].get('p_value', '-')}")
    return rows


# ----------------------------------------------------------------- charts
def make_charts(evals, cfg, outdir):
    import matplotlib.dates as mdates
    C_HY, C_B, C_NA = "#9467bd", "#1f77b4", "#7f7f7f"
    hor = cfg["evaluation"]["horizons"]
    n = len(hor)
    ncol = 2
    nrow = int(np.ceil(n / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(7.8 * ncol, 4.3 * nrow), squeeze=False)
    for ax, h in zip(axes.ravel(), hor):
        rec = next((r for r in evals if r["h"] == int(h)), None)
        if rec is None:
            ax.set_visible(False)
            continue
        dts = pd.to_datetime(rec["dates"])
        step = max(1, h // 12)
        ax.plot(dts, rec["actual"], color="black", lw=2.0, label="Actual", zorder=5)
        ax.plot(dts, rec["sarima"], color=C_B, lw=1.5, ls="--", marker="s", ms=3.5,
                markevery=step,
                label=f"SARIMA   RMSE {rec['metrics']['baseline']['RMSE']:.2f}   "
                      f"MAPE {rec['metrics']['baseline']['MAPE']:.2f}%")
        ax.plot(dts, rec["hybrid"], color=C_HY, lw=1.6, ls="-", marker="^", ms=4.0,
                markevery=step,
                label=f"SARIMA+NNAR   RMSE {rec['metrics']['hybrid']['RMSE']:.2f}   "
                      f"MAPE {rec['metrics']['hybrid']['MAPE']:.2f}%")
        if rec.get("seasonal_naive"):
            ax.plot(dts, rec["seasonal_naive"], color=C_NA, lw=1.0, ls=":", marker="v",
                    ms=3.0, markevery=step,
                    label=f"Seasonal-naive   RMSE {rec['metrics']['seasonal_naive']['RMSE']:.2f}")
        ax.set_title(f"{h}-week horizon (n={h})", fontsize=11)
        ax.set_ylabel("Cases")
        ax.grid(alpha=0.28)
        ax.legend(fontsize=7.8, framealpha=0.92)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        fig.autofmt_xdate()
    for j in range(len(hor), nrow * ncol):
        axes.ravel()[j].set_visible(False)
    fig.suptitle("Forecast accuracy by horizon - fixed origin", fontsize=13, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    p1 = os.path.join(outdir, cfg["output"]["chart_horizons"])
    fig.savefig(p1, dpi=140, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    hs = [r["h"] for r in evals]
    for key, col, lbl in (("RMSE", "#1f77b4", "RMSE"), ("MAE", "#ff7f0e", "MAE"),
                          ("MAPE", "#2ca02c", "MAPE %")):
        ax.plot(hs, [r["metrics"]["baseline"][key] for r in evals], color=col, ls="--",
                marker="s", ms=5, label=f"SARIMA  {lbl}")
        ax.plot(hs, [r["metrics"]["hybrid"][key] for r in evals], color=col, ls="-",
                marker="^", ms=6, label=f"SARIMA+NNAR  {lbl}")
    ax.set_xlabel("Forecast horizon (periods)")
    ax.set_title("Error growth by horizon - fixed origin", fontsize=12)
    ax.grid(alpha=0.28)
    ax.legend(fontsize=8, ncol=2, framealpha=0.92)
    fig.tight_layout()
    p2 = os.path.join(outdir, cfg["output"]["chart_error"])
    fig.savefig(p2, dpi=140, bbox_inches="tight")
    plt.close(fig)
    return p1, p2


# ----------------------------------------------------------------- report
def write_report(res, cfg, path):
    L = ["# SARIMA + NNAR residual-hybrid search", "",
         "Dataset-agnostic pipeline. Selection uses training data only; the test set is scored "
         "once, after selection is locked.", "",
         "## Run configuration", "",
         f"- Data: `{cfg['data']['path']}` (column `{res['data']['value_column_used']}`)",
         f"- Seasonal period: **{res['data']['seasonal_period']}** (by {res['data']['inferred_by']})",
         f"- Gap profile (days): {res['data']['gap_profile_days']} - positional indexing, "
         "seasonality aligned by row not calendar",
         f"- Train n={res['data']['train_n']}, test n={res['data']['test_n']}, "
         f"train mean {res['data']['train_mean']:.2f}, test mean {res['data']['test_mean']:.2f}",
         f"- Grid: p{cfg['sarima']['p']} d{cfg['sarima']['d']} q{cfg['sarima']['q']} "
         f"P{cfg['sarima']['P']} D{cfg['sarima']['D']} Q{cfg['sarima']['Q']}",
         f"- Residual filter: `{cfg['selection']['residual_filter']}` "
         f"(alpha={cfg['selection']['lb_alpha']})",
         f"- Grid tier **{res.get('grid', {}).get('tier', 'n/a')}** - "
         f"{res.get('grid', {}).get('candidates', '?')} candidates, "
         f"{res.get('grid', {}).get('n_jobs', '?')} worker processes",
         "",
         "## Stage 1 - SARIMA grid (train only)", "",
         f"- Fitted {len(res['stage1'])} candidates, {res['stage1_rejected']} rejected",
         f"- Survived filter `{cfg['selection']['residual_filter']}`: {res['filtered']}",
         f"- Shortlisted {res['shortlist']} by AIC", "",
         "## Stage 2 - NNAR optimisation (train only)", "",
         "| Order | Seasonal | AIC | Ljung-Box p | white? | NNAR | Val RMSE base | Val RMSE hybrid | NNAR helps? | vs baseline | per-window hybrid RMSE |",
         "|---|---|---:|---|:---:|---|---:|---:|:---:|---:|---|"]
    for r in res["stage2"]:
        lb = r.get("lb_p") or {}
        lbs = ", ".join(f"{k}:{v:.3g}" for k, v in lb.items()) if lb else "-"
        nn = r.get("nnar")
        imp = r.get("improvement_pct")
        hv = r.get("hybrid_val_rmse")
        bv = r.get("baseline_val_rmse")
        helps = r.get("nnar_helps_baseline")
        pw = r.get("per_window")
        pws = ("<br>".join(f"{w[-10:]}: {h:.1f}" for w, h in zip(pw["window"], pw["hybrid"]))
               if pw else "-")
        L.append(f"| {tuple(r['order'])} | {tuple(r['seasonal'])} | "
                 f"{r['aic']:.2f} | {lbs} | {'yes' if r.get('white_noise') else 'no'} | "
                 f"{f'lag{nn['lag']} k{nn['k']}' if nn else '-'} | "
                 f"{(f'{bv:.2f}' if bv is not None else '-')} | "
                 f"{hv:.2f} | "
                 f"{('yes' if helps else 'NO') if helps is not None else '-'} | "
                 f"{(f'{imp:+.1f}%' if imp is not None else '-')} | {pws} |")
    sel = res["selected"]
    L += ["", "## Selected", "", f"**{sel['label']}**", f"- {sel['reason']}", ""]
    d = res.get("selection_diagnostics")
    if d:
        L += ["### Ranking diagnostics", "",
              f"- Chosen by `{cfg['selection']['rank_by']}`: `{d['chosen_by_hybrid_val_rmse']}`",
              f"- Would be chosen by AIC: `{d['chosen_by_aic']}`",
              f"- Would be chosen by 'NNAR actually helps': "
              f"`{d['chosen_by_nnar_helps'] or 'none of the candidates'}`",
              f"- NNAR made validation *worse* for "
              f"**{d['candidates_where_nnar_hurts']} of {d['candidates']}** candidates",
              f"- Rank correlation between AIC and hybrid validation RMSE: "
              f"{d['aic_vs_hybrid_rank_spearman']} "
              f"(near zero or negative means AIC does not predict accuracy here)", ""]
    if sel.get("nnar"):
        L += [f"- SARIMA order {tuple(sel['order'])} seasonal {tuple(sel['seasonal'])}",
              f"- NNAR lag {sel['nnar']['lag']}, k {sel['nnar']['k']}"]
    L += ["", "## Residuals of the selected model", ""]
    for k, v in (res.get("residuals") or {}).items():
        L.append(f"- **{k}**: {v}")
    L += ["", "## Evaluation by horizon (fixed origin)", "",
          "| Horizon | n | Metric | SARIMA | +NNAR | Seasonal-naive | Improvement | DM p |",
          "|---:|---:|---|---:|---:|---:|---:|---:|"]
    for r in res["evaluation"]:
        for mk in cfg["evaluation"]["metrics"]:
            b = r["metrics"]["baseline"].get(mk)
            h_ = r["metrics"]["hybrid"].get(mk)
            nv = (r["metrics"].get("seasonal_naive") or {}).get(mk)
            imp = r["improvement_pct"].get(mk)
            L.append(f"| {r['h']} | {r['n']} | {mk} | {b:.2f} | {h_:.2f} | "
                     f"{(f'{nv:.2f}' if nv is not None else '-')} | "
                     f"{(f'{imp:+.1f}%' if imp is not None else '-')} | "
                     f"{r['dm_test'].get('p_value', '-')} |")
    L += ["", "The DM p-value is computed once per horizon on the absolute-error loss "
          "differential (hybrid minus SARIMA), not separately per metric - hence the repeated "
          "value down each horizon block. Negative mean differential favours the hybrid."]
    any_zero = any(r["metrics"]["hybrid"].get("zero_actuals_excluded", 0)
                   or r["metrics"]["baseline"].get("zero_actuals_excluded", 0)
                   for r in res["evaluation"])
    L.append("")
    L.append(f"MAPE zero-actual exclusions: "
             + (", ".join(f"h={r['h']}: {r['metrics']['hybrid'].get('zero_actuals_excluded', 0)}"
                          for r in res["evaluation"])
                if any_zero else "none - all actuals non-zero, so no MAPE exclusions apply"))
    sm = [r for r in res["evaluation"] if r.get("strata")]
    if sm:
        thr = cfg["evaluation"]["stratum_threshold"]
        L += ["", f"### Stratum split (below / at or above {thr} actual)", "",
              "| Horizon | Stratum | n | Metric | SARIMA | +NNAR |", "|---:|---|---:|---|---:|---:|"]
        for r in sm:
            for nm, s in r["strata"].items():
                lbl = f"< {thr}" if nm == "low" else f">= {thr}"
                for mk in cfg["evaluation"]["metrics"]:
                    L.append(f"| {r['h']} | {lbl} | {s['n']} | {mk} | "
                             f"{s['baseline'][mk]:.2f} | {s['hybrid'][mk]:.2f} |")
    L += ["", "## Figures", "",
          f"- `{cfg['output']['chart_horizons']}` - actual vs SARIMA vs hybrid vs "
          "seasonal-naive, one panel per horizon",
          f"- `{cfg['output']['chart_error']}` - error growth as the horizon extends", "",
          "## Limitations", "",
          f"- **Bounded search.** Grid tier `{res.get('grid', {}).get('tier', 'n/a')}` searched "
          f"{res.get('grid', {}).get('candidates', '?')} specifications. "
          f"{res.get('grid', {}).get('exclusions', '') or 'No further exclusions recorded.'} "
          "A bounded grid is not an exhaustive one.",
          "- Fixed-origin evaluation: horizon h is scored on the FIRST h test periods only. Short "
          "horizons therefore describe a narrow slice of the test year and are not representative; "
          "a rolling-origin variant would give many more error pairs.",
          "- Diebold-Mariano p-values are small-sample; with few periods they have low power and "
          "should be read as indicative only.",
          "- MAPE is undefined at zero actuals; those periods are excluded and the count is reported "
          "with every metric block.",
          "- Positional (not calendar) indexing means seasonality is aligned by row; irregular "
          "reporting gaps cause slight drift from the true calendar period (see gap profile above).",
          "- NNAR and MAPE carry small run-to-run variance; single-run results are not averaged."]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description="SARIMA + NNAR residual-hybrid search")
    ap.add_argument("--config")
    ap.add_argument("--data")
    ap.add_argument("--date-col")
    ap.add_argument("--value-col")
    ap.add_argument("--seasonal", type=int)
    ap.add_argument("--train-n", type=int)
    ap.add_argument("--horizons", help="comma-separated, e.g. 4,13,26,52")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--report-only", action="store_true",
                    help="rebuild report and charts from an existing results JSON, no refitting")
    args = ap.parse_args()

    cfg = dict(DEFAULT_CONFIG)
    if args.config:
        with open(args.config) as fh:
            cfg = merge(cfg, json.load(fh))
    if args.data:
        cfg["data"]["path"] = args.data
    if args.date_col:
        cfg["data"]["date_col"] = args.date_col
    if args.value_col:
        cfg["data"]["value_col"] = args.value_col
    if args.seasonal:
        cfg["seasonal"]["period"] = args.seasonal
    if args.train_n:
        cfg["split"]["train_n"] = args.train_n
    if args.horizons:
        cfg["evaluation"]["horizons"] = [int(x) for x in args.horizons.split(",")]
    if args.report_only:
        os.makedirs(args.outdir, exist_ok=True)
        cands = [os.path.join(args.outdir, cfg["output"]["json"]),
                 os.path.join(args.outdir, "weekly_residual_search.json")]
        for f in sorted(os.listdir(args.outdir)):
            if f.lower().endswith(".json") and os.path.join(args.outdir, f) not in cands:
                cands.append(os.path.join(args.outdir, f))
        jp = None
        for c in cands:
            if not os.path.exists(c):
                continue
            try:
                with open(c, encoding="utf-8") as fh:
                    probe = json.load(fh)
            except Exception:
                continue
            if isinstance(probe, dict) and "evaluation" in probe and "selected" in probe:
                jp = c
                break
        if jp is None:
            raise SystemExit(f"--report-only: no pipeline results JSON found in {args.outdir}")
        with open(jp, encoding="utf-8") as fh:
            saved = json.load(fh)
        cfg2 = saved.get("config", cfg)
        log(f"rebuilding report from {jp}")
        rp = os.path.join(args.outdir, cfg2["output"]["report"])
        write_report(saved, cfg2, rp)
        log(f"wrote {rp}")
        p1, p2 = make_charts(saved["evaluation"], cfg2, args.outdir)
        log(f"wrote {p1}")
        log(f"wrote {p2}")
        log("DONE")
        return

    if not cfg["data"]["path"]:
        ap.error("need --data or a config with data.path")

    os.makedirs(args.outdir, exist_ok=True)
    log(f"config data: {json.dumps(cfg['data'])}")

    series, prof = load_series(cfg)
    period, inferred_by = infer_seasonal(series, cfg)

    # resolve grid tier -> concrete search ranges (bounded, documented)
    tier = cfg.get("grid_tier", "fast")
    if tier in GRID_TIERS:
        cfg["sarima"] = dict(cfg["sarima"])
        for _k in ("p", "d", "q", "P", "D", "Q"):
            cfg["sarima"][_k] = list(GRID_TIERS[tier][_k])
    n_grid = 1
    for _k in ("p", "d", "q", "P", "D", "Q"):
        n_grid *= len(cfg["sarima"][_k])
    n_jobs = int(cfg.get("n_jobs") or 0) or max(1, (os.cpu_count() or 4) - 1)
    log(f"grid tier '{tier}' -> {n_grid} candidates {cfg['sarima']} | {n_jobs} workers")
    prof.update({"seasonal_period": period, "inferred_by": inferred_by})
    log(f"seasonal period {period} (by {inferred_by}); gaps {prof['gap_profile_days']}")

    train, test = make_split(series, cfg)
    log(f"split: train n={len(train)} test n={len(test)}")
    diag = diagnose(train, cfg)
    log(f"diagnostics: adf={diag.get('adf_raw')} suggested_d={diag.get('suggested_d')}")

    cands, rejected = stage1_grid(train, cfg, period, n_jobs)
    filt, mode = stage1_filter(cands, cfg)
    filt.sort(key=lambda c: c["aic"])
    shortlist = filt[: int(cfg["selection"]["candidates_to_refine"])]
    log(f"stage 1: {len(cands)} fitted, {len(filt)} survive filter '{mode}', "
        f"{len(shortlist)} shortlisted")
    if not shortlist:
        raise SystemExit("no candidates survived the residual filter; check "
                         "selection.residual_filter or widen the grid")

    stage2_rows = stage2(shortlist, train, cfg, n_jobs)
    ok2 = [r for r in stage2_rows if r.get("nnar")]
    if not ok2:
        errs = [r.get("error") for r in stage2_rows if r.get("error")][:3]
        raise SystemExit("stage 2 produced no usable candidate: " + " | ".join(map(str, errs)))
    rank_by = cfg["selection"]["rank_by"]
    ok2.sort(key=lambda r: r[rank_by] if r.get(rank_by) is not None else 1e18)
    winner = ok2[0]
    log(f"SELECTED SARIMA{tuple(winner['order'])}{tuple(winner['seasonal'])} "
        f"+ NNAR{winner['nnar']}")

    # Diagnostic only: what the alternative ranking rules would have chosen.
    # Ranking on one 52-week validation block is noisy, and the hybrid score tracks
    # the baseline almost exactly - so the choice is reported, not hidden.
    def _lbl(r):
        return f"SARIMA{tuple(r['order'])}{tuple(r['seasonal'])}"
    aic_rank = sorted(ok2, key=lambda r: r["aic"])
    helps = [r for r in ok2 if r.get("nnar_helps_baseline")]
    alt = {"chosen_by_hybrid_val_rmse": _lbl(winner),
           "chosen_by_aic": _lbl(aic_rank[0]),
           "chosen_by_nnar_helps": (_lbl(min(helps, key=lambda r: r["hybrid_val_rmse"]))
                                    if helps else None),
           "candidates_where_nnar_hurts": sum(
               1 for r in ok2 if not r.get("nnar_helps_baseline")),
           "candidates": len(ok2),
           "aic_vs_hybrid_rank_spearman": None}
    try:
        a = [r["aic"] for r in ok2]
        h = [r["hybrid_val_rmse"] for r in ok2]
        ra = pd.Series(a).rank().tolist()
        rh = pd.Series(h).rank().tolist()
        alt["aic_vs_hybrid_rank_spearman"] = round(
            float(pd.Series(ra).corr(pd.Series(rh))), 4)
    except Exception:
        pass
    log(f"diagnostic: AIC would pick {_lbl(aic_rank[0])}; "
        f"NNAR hurts in {alt['candidates_where_nnar_hurts']}/{len(ok2)} candidates; "
        f"AIC-vs-hybrid rank corr {alt['aic_vs_hybrid_rank_spearman']}")

    base_fc, hyb_fc, naive, resid = build_winner(train, winner, cfg)
    log("evaluating horizons")
    evals = evaluate(test, base_fc, hyb_fc, naive, cfg, test.index)

    # drop cached fit artefacts before serialising (they are large and not reportable)
    for r in list(cands) + list(stage2_rows):
        r.pop("_resid", None)
        r.pop("_fc", None)
        r.pop("_base_val", None)

    lb_lags = [period, 2 * period] if period > 1 else [1, 2]
    try:
        lb = acorr_ljungbox(pd.Series(resid).dropna(), lags=lb_lags, return_df=True)
        pv = {str(int(k)): float(v) for k, v in zip(lb_lags, lb["lb_pvalue"])}
        white = all(v > cfg["selection"]["lb_alpha"] for v in pv.values())
    except Exception as ex:
        pv, white = {"error": str(ex)}, None
    sig = sorted(r["h"] for r in evals if r["dm_test"].get("significant"))
    verdict = ("structure remains in the residuals (non-white), as the filter targets"
               if white is False else
               "residuals are white noise - the filter's intent was not met")
    verdict += (f"; NNAR improved significantly at horizon(s) {sig}" if sig
                else "; no horizon showed a statistically significant NNAR improvement")

    res = {
        "config": cfg,
        "grid": {"tier": tier, "candidates": n_grid, "n_jobs": n_jobs,
                 "ranges": {k: cfg["sarima"][k] for k in ("p", "d", "q", "P", "D", "Q")},
                 "exclusions": TIER_NOTES.get(tier, "")},
        "data": {**prof, "train_n": int(len(train)), "test_n": int(len(test)),
                  "train_mean": float(train.mean()), "test_mean": float(test.mean())},
        "diagnostics": diag,
        "stage1": cands, "stage1_rejected": rejected,
        "filtered": len(filt), "shortlist": len(shortlist),
        "stage2": stage2_rows,
        "selection_diagnostics": alt,
        "selected": {"label": f"SARIMA{tuple(winner['order'])}{tuple(winner['seasonal'])}"
                                f" + NNAR(lag {winner['nnar']['lag']}, k {winner['nnar']['k']})",
                     "reason": f"lowest {rank_by} among {len(ok2)} refined candidates",
                     "order": winner["order"], "seasonal": winner["seasonal"],
                     "nnar": winner["nnar"], "aic": winner["aic"]},
        "residuals": {"ljung_box_p": pv, "white_noise": white,
                      "learnable_by_nnar": (white is False), "verdict": verdict},
        "evaluation": evals,
        "runtime_seconds": round(time.time() - T0, 2),
    }

    jp = os.path.join(args.outdir, cfg["output"]["json"])
    with open(jp, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, default=str)
    log(f"wrote {jp}")

    rp = os.path.join(args.outdir, cfg["output"]["report"])
    write_report(res, cfg, rp)
    log(f"wrote {rp}")

    # Charts are optional: a headless/offline run sets either output path to null.
    charts = [cfg["output"].get("chart_horizons"), cfg["output"].get("chart_error")]
    if all(charts):
        try:
            p1, p2 = make_charts(evals, cfg, args.outdir)
            log(f"wrote {p1}")
            log(f"wrote {p2}")
        except Exception as ex:
            log(f"chart generation failed: {type(ex).__name__}: {ex}")
            traceback.print_exc()
    else:
        log("chart output disabled by config")

    log("DONE")


if __name__ == "__main__":
    main()