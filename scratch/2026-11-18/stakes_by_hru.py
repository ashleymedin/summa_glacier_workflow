#!/usr/bin/env python3
"""Winter and summer balances of each HRU's clean-ice glacier domain in reruns, against the stakes nearest in elevation
(as scratch/2026-11-16/stake_seasons.py, but on calibration_rerun/sample_<run> output). Balances in m w.e., split into
the calibration (WY2006-15) and held-out (WY2016-) years.

    stakes_by_hru.py wolverine_added:472,472_raingrad gulkana_general:392_nrg
"""
import glob
import os
import sys

import netCDF4 as nc4
import numpy as np
import pandas as pd

WF = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
STAKES = {"wolverine": "Wolverine", "gulkana": "Gulkana"}


def domain_mass(case, run):
    base = f"{WF}/runs/{case}/calibration_rerun/sample_{run}"
    f = [p for p in glob.glob(f"{base}/output/*_day.nc") if "spinup" not in p][0]
    with nc4.Dataset(f) as d:
        time = pd.to_datetime(nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False,
                                           only_use_python_datetimes=True)).normalize()
        gm = np.ma.filled(d["glacMass4AreaChange_mean"][:].astype(float), np.nan)
        elev = np.ma.filled(d["DOMelev_mean"][:].astype(float), np.nan)
        typ = np.ma.filled(d["domType"][:].astype(int), -1)
    grad = 0.0
    for line in open(f"{base}_settings/localParamInfo.txt"):
        if line.split("|")[0].strip() == "precipElevGrad":
            grad = float(line.split("|")[1])
    change = np.diff(gm, axis=0, prepend=gm[:1])
    reset = (time.month == 10) & (time.day == 2)  # the yearly area update zeroes the counter on 2 October
    change[reset] = gm[reset]
    mass = np.cumsum(np.nan_to_num(change), axis=0) / 1000.0
    series = {}
    for h in range(typ.shape[0]):
        m = int(np.argmax(typ[h] == 2))
        series[h] = (pd.Series(mass[:, h, m], index=time), float(np.nanmedian(elev[:, h, m])))
    return series, grad


def compare(case, run):
    series, grad = domain_mass(case, run)
    name = STAKES[case.split("_")[0]]
    csv = f"{WF}/data/domain_{name}/observations/storage/mass_balance/Input_{name}_Glaciological_Data.csv"
    s = pd.read_csv(csv, parse_dates=["spring_date", "fall_date"])
    t0, t1 = next(iter(series.values()))[0].index[[0, -1]]
    prev = pd.read_csv(csv, parse_dates=["fall_date"])[["Year", "site_name", "fall_date"]]
    prev["Year"] += 1
    s = s.merge(prev.rename(columns={"fall_date": "prev_fall"}), on=["Year", "site_name"], how="left")
    s["prev_fall"] = s.prev_fall.fillna(pd.to_datetime((s.Year - 1).astype(str) + "-10-01"))
    s = s[(s.prev_fall >= t0) & (s.fall_date <= t1) & (s.Year >= 2006)]
    rows = []
    for _, r in s.iterrows():
        h = min(series, key=lambda k: abs(series[k][1] - r.elevation))
        m, z = series[h]
        at = lambda t: float(m.asof(t))  # noqa: E731
        bw = (at(r.spring_date) - at(r.prev_fall)) * (1 + grad * (r.elevation - z))
        bs = at(r.fall_date) - at(r.spring_date)
        rows.append(dict(year=r.Year, hru=h + 1, z=r.elevation, bw_obs=r.bw, bw_sim=bw, d_bw=bw - r.bw, d_bs=bs - (r.ba - r.bw), d_ba=bw + bs - r.ba))
    t = pd.DataFrame(rows)
    t["period"] = np.where(t.year <= 2015, "cal", "held")
    g = t.groupby(["hru", "period"])[["z", "bw_obs", "bw_sim", "d_bw", "d_bs", "d_ba"]].mean().round(2)
    g["n"] = t.groupby(["hru", "period"]).size()
    print(f"== {case} {run}: sim - obs by HRU (m w.e.; winter, summer, annual)")
    print(g.unstack("period").to_string())


for spec in sys.argv[1:]:
    case, runs = spec.split(":")
    for run in runs.split(","):
        compare(case, run)
