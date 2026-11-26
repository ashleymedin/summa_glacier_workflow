#!/usr/bin/env python3
"""Paired upland snow test: lemon_grus (flat) against lemon_grus_snow (rise), one calibration name each (default cheap_adv).
Prints each Pareto front with its held-out scores and the upland multiplier against its bounds, the balanced members
(post_merge's pick: of the discharge-stakes front, nearest the ideal corner, each scaled by its span), and front medians.

    python lemon_pair_compare.py [name]
"""
import glob
import os
import sys

import netCDF4 as nc4
import numpy as np
import pandas as pd
import tomllib

RUNS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "runs"))
NAME = sys.argv[1] if len(sys.argv) > 1 else "cheap_adv"
UP = "frozenPrecipMultip@upland"
pd.set_option("display.width", 220)


def front(case):
    r = os.path.join(RUNS, case, NAME)
    with nc4.Dataset(glob.glob(os.path.join(r, "output", "*_calibration.nc"))[0]) as d:
        tn = [t.strip() for t in d["objective"].target.split(",")]
        o = pd.DataFrame(np.ma.filled(d["objective"][:].astype(float), np.nan), columns=tn, index=np.arange(1, d.dimensions["sample"].size + 1))
        p = pd.DataFrame({v: np.ma.filled(d[v][:].astype(float), np.nan) for v in (UP, "frozenPrecipMultip@glacier_gru1", "frozenPrecipMultip@glacier_gru2", "k_snow", "albedoMax")}, index=o.index)
        f = o.index[np.asarray(d["pareto_front"][:]) == 1]
    lo, hi = (lambda b: (b["lower"], b["upper"]))(tomllib.load(open(os.path.join(r, "config.toml"), "rb"))["calibration"]["spatial_multipliers"][UP])
    e = pd.read_csv(os.path.join(RUNS, case, NAME + "_evaluation", "evaluation.csv"), index_col="sample")
    t = pd.concat([o.loc[f, ["discharge", "mass_balance"]].add_prefix("cal_obj_"), p.loc[f], e.reindex(f)], axis=1)
    k, m = t.cal_obj_discharge, t.cal_obj_mass_balance
    t["front2"] = [not ((k >= k[i]) & (m <= m[i]) & ((k > k[i]) | (m < m[i]))).any() for i in t.index]  # discharge and stakes only, as post_merge
    k, m = k[t.front2], m[t.front2]
    span = lambda x: (x.max() - x.min()) or 1.0  # noqa: E731
    bal = (np.hypot((k.max() - k) / span(k), (m - m.min()) / span(m))).idxmin()
    return t.sort_values("cal_obj_discharge"), bal, (lo, hi)


rows = {}
for case in ("lemon_grus", "lemon_grus_snow"):
    t, bal, (lo, hi) = front(case)
    print(f"\n== {case} {NAME}: front of {len(t)}, upland multiplier bounds {lo}-{hi}, balanced sample {bal}")
    print(t.round(3).to_string())
    n_hi = int((t[UP] > hi - 0.05 * (hi - lo)).sum())
    print(f"upland multiplier {t[UP].min():.2f}-{t[UP].max():.2f}; {n_hi} of {len(t)} within 5% of the upper bound")
    rows[case + " balanced"] = t.loc[bal]
    rows[case + " median"] = t.median()
cols = ["cal_obj_discharge", "cal_obj_mass_balance", "cal_discharge", "cal_mass_balance", "cal_hugonnet_01506", "cal_hugonnet_01105", "eval_discharge", "eval_mass_balance", UP]
print("\n" + pd.DataFrame(rows).T[[c for c in cols if c in rows[next(iter(rows))].index]].round(3).to_string())
