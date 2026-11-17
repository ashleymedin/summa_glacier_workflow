#!/usr/bin/env python3
"""Which elevation form does the snowfall correction take? Stake winter balance over raw ERA5 snowfall, against
stake elevation, fitted three ways.

For each stake-year (WY2005-2024, stakes above the terminus cutoff) the ERA5 precipitation of the HRU nearest the
stake (general forcing divided by its CHELSA ratio, remap.csv) is summed over the stake's fall-to-spring interval in
the hours whose air, lapsed to the stake with remap.csv's monthly rate, is below 274.16 K (SUMMA's default split
midpoint). R = bw / that snowfall.

  linear       R = c (1 + g (z - z_ref))          2 parameters (the multiplier and precipElevGrad)
  exponential  R = c exp(b (z - z_ref))           2 parameters
  exp, c = 1   R = exp(b (z - z_ref))             1 parameter: ERA5 right at its own orography

z_ref is ERA5's mean orography over the domain's cells (pressure-level forcing memory: Wolverine ~770 m, Gulkana
~1420 m). Fits are least squares in log R, stake-years weighted alike.

    snow_ratio_form.py
"""
import glob
import os

import netCDF4 as nc4
import numpy as np
import pandas as pd
from scipy.optimize import least_squares

G = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
DOMS = {"Wolverine": dict(z_ref=770.0, min_z=800.0), "Gulkana": dict(z_ref=1424.0, min_z=1300.0)}


def era5_orography(name):
    p = glob.glob(os.path.join(G, f"data/domain_{name}*/forcing/raw_levels/domain_{name}_ERA5_orography.nc"))
    if not p:
        return None
    with nc4.Dataset(p[0]) as d:
        v = [k for k in d.variables if k.lower() in ("z", "orography", "elevation", "orog")]
        z = np.asarray(d[v[0]][:], float)
        return float(np.nanmean(z / 9.80665 if z.max() > 20000 else z))


def forcing(name):
    base = os.path.join(G, f"data/domain_{name}_general/forcing/SUMMA_input")
    rows = {}
    for line in open(os.path.join(base, "remap.csv")):
        k, *v = line.strip().split(",")
        rows[k] = [float(x) for x in v]
    ratio, lapse = np.array(rows["precip_ratio"]), np.array(rows["lapse_rate_K_per_km"]) / 1000.0
    t, p, a = [], [], []
    for f in sorted(glob.glob(os.path.join(base, "*.nc"))):
        with nc4.Dataset(f) as d:
            t.append(pd.to_datetime(nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False,
                                                 only_use_python_datetimes=True)))
            p.append(np.asarray(d["pptrate"][:], float) / ratio[None, :] * 3600.0)  # mm per hour
            a.append(np.asarray(d["airtemp"][:], float))
    with nc4.Dataset(os.path.join(G, f"data/domain_{name}_general/settings/SUMMA/attributes.nc")) as d:
        z_hru = np.asarray(d["elevation"][:], float)
    return pd.DatetimeIndex(np.concatenate(t)), np.concatenate(p), np.concatenate(a), z_hru, lapse


def ratios(name):
    t, p, a, z_hru, lapse = forcing(name)
    stakes = pd.read_csv(os.path.join(G, f"data/domain_{name}/observations/storage/mass_balance/Input_{name}_Glaciological_Data.csv"),
                         parse_dates=["spring_date", "fall_date"])
    prev = stakes[["Year", "site_name", "fall_date"]].copy()
    prev["Year"] += 1
    s = stakes.merge(prev.rename(columns={"fall_date": "prev_fall"}), on=["Year", "site_name"], how="left")
    s["prev_fall"] = s.prev_fall.fillna(pd.to_datetime((s.Year - 1).astype(str) + "-10-01"))
    s = s[(s.Year >= 2005) & (s.Year <= 2024) & np.isfinite(s.bw) & (s.elevation >= DOMS[name]["min_z"])]
    out = []
    for _, r in s.iterrows():
        j = int(np.argmin(abs(z_hru - r.elevation)))
        sel = (t > r.prev_fall) & (t <= r.spring_date)
        if sel.sum() < 24 * 120:
            continue
        ta = a[sel, j] + lapse[t[sel].month - 1] * (r.elevation - z_hru[j])
        snow = p[sel, j][ta < 274.16].sum() / 1000.0
        if snow > 0.05 and r.bw > 0:
            out.append((r.elevation, r.bw / snow))
    return np.array(out)


def fit(z, R, z_ref):
    lr = np.log(R)
    lin = least_squares(lambda q: np.log(np.maximum(q[0] * (1 + q[1] * (z - z_ref)), 1e-6)) - lr, [1.0, 0.001])
    ex = least_squares(lambda q: np.log(q[0]) + q[1] * (z - z_ref) - lr, [1.0, 0.001], bounds=([1e-3, -1], [100, 1]))
    ex1 = least_squares(lambda q: q[0] * (z - z_ref) - lr, [0.001])
    rms = lambda r: float(np.sqrt(np.mean(r.fun ** 2)))  # noqa: E731
    return lin, ex, ex1, rms


for name, d in DOMS.items():
    zo = era5_orography(name)
    z_ref = zo if zo else d["z_ref"]
    zr = ratios(name)
    z, R = zr[:, 0], zr[:, 1]
    lin, ex, ex1, rms = fit(z, R, z_ref)
    print(f"{name}: {len(z)} stake-years, {z.min():.0f}-{z.max():.0f} m, z_ref {z_ref:.0f} m (ERA5 orography{'' if zo else ', assumed'})")
    print(f"  R by elevation band: " + ", ".join(f"{lo:.0f}-{lo + 200:.0f} m {np.median(R[(z >= lo) & (z < lo + 200)]):.2f}"
                                              for lo in np.arange(np.floor(z.min() / 200) * 200, z.max(), 200) if ((z >= lo) & (z < lo + 200)).any()))
    print(f"  linear       c {lin.x[0]:.2f}  g {lin.x[1]:.5f} /m          rms log R {rms(lin):.3f}")
    print(f"  exponential  c {ex.x[0]:.2f}  b {ex.x[1]:.5f} /m          rms log R {rms(ex):.3f}")
    print(f"  exp, c = 1           b {ex1.x[0]:.5f} /m          rms log R {rms(ex1):.3f}")
