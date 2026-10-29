#!/usr/bin/env python3
"""
ICD-10 Fixed-Split Forecasting - Prophet + XGBoost only
"""

import os
import sys
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "1")
os.environ.setdefault("TF_NUM_INTEROP_THREADS", "1")

import argparse
import json
import warnings
from datetime import datetime
import shutil
import tempfile
import time

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

try:
    from threadpoolctl import threadpool_limits
    _HAS_THREADPOOLCTL = True
except Exception:
    _HAS_THREADPOOLCTL = False

CSV_PATH = "antipolo_top5_icd10_monthly.csv"
BLOCKS_ALL = ["A00-A09", "A15-A19", "A80-A89", "B00-B09", "B25-B34", "B85-B89", "B90-B94"]
REGISTRY = ["prophet", "hyb_prophet_xgboost"]

M_SEASON = 12
RNG_SEED = 12345

HYBRID_BASES = ["prophet"]
ML_KEYS = ["xgboost"]
BASE_SHORT = {"prophet": "prophet"}
ML_LABEL = {"xgboost": "XGBoost"}
BASE_LABEL = {"prophet": "Prophet"}
HYBRID_SPEC = {f"hyb_{BASE_SHORT[b]}_{m}": (b, m) for b in HYBRID_BASES for m in ML_KEYS}

MODEL_COLOR = {"prophet": "#1f77b4"}
MODEL_MARK = {"prophet": "^"}
HYBRID_ACCENT = "#c2185b"

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 160, "font.size": 9,
    "axes.grid": True, "grid.alpha": 0.3, "axes.edgecolor": "#444",
    "figure.facecolor": "white", "axes.titlesize": 10,
    "axes.titleweight": "bold",
})

def _init_worker():
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
              "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS",
              "TF_NUM_INTRAOP_THREADS", "TF_NUM_INTEROP_THREADS"):
        os.environ[v] = "1"
    warnings.filterwarnings("ignore")
    if _HAS_THREADPOOLCTL:
        try:
            threadpool_limits(limits=1)
        except Exception:
            pass

def display_name(key):
    if key in BASE_LABEL:
        return BASE_LABEL[key]
    if key in HYBRID_SPEC:
        b, m = HYBRID_SPEC[key]
        return f"{BASE_LABEL[b]} + {ML_LABEL[m]}"
    return key

def _save_fig(fig, fname):
    """Write through the system temp dir to handle synced Downloads folders."""
    os.makedirs(os.path.dirname(fname), exist_ok=True)
    tmp = os.path.join(tempfile.gettempdir(), os.path.basename(fname))
    fig.savefig(tmp, dpi=160)
    for _ in range(20):
        try:
            shutil.copyfile(tmp, fname)
            try:
                os.remove(tmp)
            except OSError:
                pass
            return fname
        except OSError:
            time.sleep(0.5)
    shutil.copyfile(tmp, fname)
    return fname

def save_forecast_chart(block_code, g, y_test, split_info, models):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "graphs_style")
    os.makedirs(output_dir, exist_ok=True)

    data = g["cases"].values.astype(float)
    idx = pd.DatetimeIndex(pd.to_datetime(
        dict(year=g["year"], month=g["month_number"], day=1)))
    n_train = split_info["n_train"]
    oi = n_train - 1
    h = len(y_test)
    test_idx = idx[oi + 1:oi + 1 + h]
    oi_val = float(data[oi]) if 0 <= oi < len(data) else float(data[0])

    def series_style(key):
        if key in HYBRID_SPEC:
            return HYBRID_ACCENT, "-", "D", True, display_name(key)
        return MODEL_COLOR[key], "--", MODEL_MARK[key], False, display_name(key)

    fig, axes = plt.subplots(2, 1, figsize=(11, 8.4))

    # ---- top panel: full record ----
    ax = axes[0]
    act_x = np.concatenate([idx[:oi + 1], test_idx])
    act_y = np.concatenate([np.asarray(data[:oi + 1]), np.asarray(y_test)])
    ax.plot(act_x, act_y, color="#333", lw=1.4, label="actual")
    if len(test_idx) > 0:
        ax.axvspan(test_idx[0], test_idx[-1], color="#ffd966", alpha=0.32, zorder=0)
    if 0 <= oi < len(idx):
        ax.axvline(idx[oi], color="#c00", ls="--", lw=1.1)

    conn_x = np.concatenate([[idx[oi]], test_idx]) if 0 <= oi < len(idx) else test_idx
    for key in REGISTRY:
        if key not in models:
            continue
        pred = np.asarray(models[key], dtype=float)
        if len(pred) != h:
            continue
        col, ls, marker, big, label = series_style(key)
        conn_y = np.concatenate([[oi_val], pred])
        ax.plot(conn_x, conn_y, lw=2.7 if big else 1.4, ls=ls, marker=marker,
                ms=5.0 if big else 3.0, color=col, label=label,
                zorder=6 if big else 3, alpha=1.0 if big else 0.9)
    ax.set_title(f"{block_code} - forecasts against the full record")
    ax.set_ylabel("consultations")
    ax.legend(fontsize=6.8, ncol=2, loc="upper left", framealpha=0.92)
    ax.tick_params(labelsize=7)

    # ---- bottom panel: detail on test window ----
    ax = axes[1]
    tail_from = max(0, oi - 11)
    act_x2 = np.concatenate([idx[tail_from:oi + 1], test_idx])
    act_y2 = np.concatenate([data[tail_from:oi + 1], np.asarray(y_test)])
    ax.plot(act_x2, act_y2, color="#333", lw=2.0, marker="o", ms=4.2, label="actual")
    if len(test_idx) > 0:
        ax.axvspan(test_idx[0], test_idx[-1], color="#ffd966", alpha=0.32, zorder=0)
    if 0 <= oi < len(idx):
        ax.axvline(idx[oi], color="#c00", ls="--", lw=1.2)
    for key in REGISTRY:
        if key not in models:
            continue
        pred = np.asarray(models[key], dtype=float)
        if len(pred) != h:
            continue
        col, ls, marker, big, label = series_style(key)
        conn_y = np.concatenate([[oi_val], pred])
        ax.plot(conn_x, conn_y, lw=2.7 if big else 1.7, marker=marker,
                ms=5.4 if big else 3.4, ls=ls, color=col, label=label,
                zorder=6 if big else 3, alpha=1.0 if big else 0.9)
    ax.set_title(f"{block_code} - detail on the {h}-month test window")
    ax.set_ylabel("consultations")
    ax.tick_params(labelsize=7)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=7.4,
               framealpha=0.95, borderaxespad=1.4)
    fig.autofmt_xdate()
    fig.tight_layout(rect=[0, 0.075, 1, 1])

    fname = os.path.join(output_dir, f"{block_code}_hybrid_hyb_prophet_xgboost.png")
    _save_fig(fig, fname)
    plt.close(fig)
    print(f"Saved {fname}")

def load_data(csv_path=CSV_PATH):
    return pd.read_csv(csv_path)

def get_block_series(df, code):
    g = df[df["icd10_code"] == code].copy()
    g = g.sort_values(["year", "month_number"]).reset_index(drop=True)
    return g

def compute_mase_scale(y_all):
    y_all = np.asarray(y_all, float)
    if len(y_all) <= M_SEASON:
        diffs = np.abs(np.diff(y_all))
        if len(diffs) == 0 or np.mean(diffs) == 0:
            return 1.0
        return float(np.mean(diffs))
    diffs = np.abs(y_all[M_SEASON:] - y_all[:-M_SEASON])
    diffs = diffs[np.isfinite(diffs)]
    if len(diffs) == 0 or np.mean(diffs) == 0:
        diffs2 = np.abs(np.diff(y_all))
        diffs2 = diffs2[np.isfinite(diffs2)]
        if len(diffs2) == 0:
            return 1.0
        return float(np.mean(diffs2))
    return float(np.mean(diffs))

def get_fixed_split(g, code):
    years = sorted(g['year'].unique())
    if len(years) == 0:
        raise ValueError("No years found")
    if code == "A80-A89":
        train_years = [y for y in years if y in (2023, 2024)]
        test_years = [y for y in years if y == 2025]
        if len(train_years) == 0 or len(test_years) == 0:
            train_years = years[:-1] if len(years) >= 2 else years
            test_years = [years[-1]] if len(years) >= 1 else []
    else:
        if len(years) == 1:
            train_years = years
            test_years = []
        else:
            train_years = years[:-1]
            test_years = [years[-1]]
    train_mask = g['year'].isin(train_years)
    test_mask = g['year'].isin(test_years)
    y_train = g[train_mask]['cases'].values.astype(float)
    y_test = g[test_mask]['cases'].values.astype(float)
    split_info = {"years_all": list(years), "train_years": list(train_years), "test_years": list(test_years), "n_train": int(len(y_train)), "n_test": int(len(y_test))}
    return y_train, y_test, split_info

def _clip(x):
    return np.maximum(np.asarray(x, float), 0.0)

def _synthetic_ds(n):
    return pd.date_range("2000-01-01", periods=n, freq="MS")

def _lag_matrix(y, lags):
    y = np.asarray(y, float)
    if len(y) < lags:
        return np.array([]), np.array([])
    X = np.column_stack([y[lags - i - 1: len(y) - i - 1] for i in range(lags)])
    return X, y[lags:]

def _recursive_predict(model, series, h, lags=12, clip=True):
    hist = list(np.asarray(series, float))
    out = []
    for _ in range(h):
        if len(hist) < lags:
            x = np.array([hist[::-1] + [hist[0]] * (lags - len(hist))])
        else:
            x = np.array([[hist[-1 - i] for i in range(lags)]], float)
        try:
            v = float(model.predict(x)[0])
        except Exception:
            v = float(np.mean(hist[-lags:]) if len(hist) >= lags else np.mean(hist))
        if clip:
            v = max(v, 0.0)
        out.append(v)
        hist.append(v)
    return np.array(out, float)

def fit_prophet(y_train, h):
    try:
        from prophet import Prophet
        y = np.asarray(y_train, float)
        ds = _synthetic_ds(len(y))
        m = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False, seasonality_mode='additive', uncertainty_samples=0)
        m.fit(pd.DataFrame({"ds": ds, "y": y}))
        fitted = np.nan_to_num(np.asarray(m.predict(pd.DataFrame({"ds": ds}))["yhat"].values, float), nan=0.0)
        fut = pd.DataFrame({"ds": pd.date_range(ds[-1] + pd.offsets.MonthBegin(), periods=h, freq="MS")})
        fc = _clip(np.asarray(m.predict(fut)["yhat"].values, float))
        return fitted, fc
    except Exception:
        fc = np.array([np.mean(y_train[-12:]) if len(y_train)>=12 else np.mean(y_train)] * h)
        return np.array(y_train), _clip(fc)

def fit_prophet_xgboost(y_train, h):
    try:
        fitted_prophet, fc_prophet = fit_prophet(y_train, h)
        resid = y_train - fitted_prophet
        import xgboost as xgb
        lags = 12
        if len(resid) < lags + 5:
            return fitted_prophet, fc_prophet
        X, y_r = _lag_matrix(resid, lags)
        if len(X) < 5:
            return fitted_prophet, fc_prophet
        model = xgb.XGBRegressor(max_depth=6, learning_rate=0.3, n_estimators=1000, subsample=.9, colsample_bytree=.9, reg_alpha=1.0, reg_lambda=1.0, random_state=RNG_SEED, n_jobs=1)
        model.fit(X, y_r)
        corr_fc = _recursive_predict(model, resid, h, lags, clip=False)
        corr_fc = np.clip(corr_fc, -1.0, 1.0)
        pred_hyb = _clip(fc_prophet + 0.1 * corr_fc)
        return fitted_prophet, pred_hyb
    except Exception:
        fitted_prophet, fc_prophet = fit_prophet(y_train, h)
        return fitted_prophet, fc_prophet

def point_metrics(actual, pred, scale=None):
    a = np.asarray(actual, float)
    p = np.asarray(pred, float)
    e = p - a
    mae = float(np.mean(np.abs(e)))
    rmse = float(np.sqrt(np.mean(e ** 2)))
    out = {"mae": mae, "rmse": rmse, "n": int(len(a))}
    if scale is not None and np.isfinite(scale) and scale > 0:
        out["mase"] = mae / float(scale)
    else:
        out["mase"] = float("nan")
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", type=str, default=None)
    ap.add_argument("--out-json", type=str, default="icd10_prophet_xgboost_tuning_results.json")
    args = ap.parse_args()

    print("=== ICD-10 Forecasting: Prophet + XGBoost ===")
    df = load_data(CSV_PATH)
    if args.blocks:
        blocks_to_run = [b.strip() for b in args.blocks.split(",")]
    else:
        blocks_to_run = BLOCKS_ALL

    all_metrics = []
    for code in blocks_to_run:
        print(f"Processing {code}...")
        g = get_block_series(df, code)
        y_train, y_test, split_info = get_fixed_split(g, code)
        h = len(y_test)
        mase_scale = compute_mase_scale(g['cases'].values.astype(float))
        results = {}
        _, fc_prophet = fit_prophet(y_train, h)
        results['prophet'] = fc_prophet
        _, fc_phx = fit_prophet_xgboost(y_train, h)
        results['hyb_prophet_xgboost'] = fc_phx
        save_forecast_chart(code, g, y_test, split_info, results)
        for mname in REGISTRY:
            pred = results.get(mname, np.zeros(h))
            met = point_metrics(y_test, pred, mase_scale)
            all_metrics.append({"block": code, "model": mname, "model_name": display_name(mname), "mae": met["mae"], "rmse": met["rmse"], "mase": met["mase"]})

    output = {"generated": datetime.now().isoformat(), "blocks": blocks_to_run, "registry": REGISTRY, "all_metrics": all_metrics}
    with open(args.out_json, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"Wrote {args.out_json}")
    df_res = pd.DataFrame(all_metrics)
    for block in blocks_to_run:
        sub = df_res[df_res['block']==block].sort_values('mae')
        print(f"\n=== {block} ===")
        print(sub[['model_name','mae','rmse','mase']].to_string(index=False))

if __name__ == "__main__":
    main()
