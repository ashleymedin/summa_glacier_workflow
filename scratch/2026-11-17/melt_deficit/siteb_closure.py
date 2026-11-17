#!/usr/bin/env python3
"""Turbulent heat needed at Gulkana Site B, 2024, against the bulk flux from the AWS's own wind (2.3 m), air
temperature and humidity (2 m) over a 0 degC surface, under SUMMA's stable functions with the Andreas scalar
roughness.

Needed = stake melt energy - AWS net shortwave - (forcing LWin at HRU 2 - 315.6), over windows when the
surface is melting (snow isothermal from 21 Jun, ice from 19 Jul).
"""
import glob
import os

import netCDF4 as nc4
import numpy as np
import pandas as pd

G = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
C = os.path.join(G, "data/domain_Gulkana/observations/campaigns/wilson_2024")
FRC = os.path.join(G, "data/domain_Gulkana/forcing/SUMMA_input/station_corrected")
LF, CP, K, NU = 3.34e5, 1005.0, 0.4, 1.3e-5

rows = []
for f in sorted(glob.glob(os.path.join(FRC, "*_20240[6-8].nc"))):
    with nc4.Dataset(f) as d:
        t = pd.to_datetime(nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False,
                                        only_use_python_datetimes=True))
        j = list(np.asarray(d["hruId"][:])).index(2)
        rows.append(pd.DataFrame({"LWin": d["LWRadAtm"][:, j], "P": d["airpres"][:, j]}, index=t))
frc = pd.concat(rows)
a = pd.read_csv(os.path.join(C, "1_meteo/gulkanaB_AWS_2024.csv"), skiprows=[1, 2], parse_dates=["TIMESTAMP"],
                date_format="%m/%d/%Y %H:%M").set_index("TIMESTAMP")
a = a[["AirTC_Avg", "RH", "WS_ms_Avg", "SWUpper_Avg", "SWLower_Avg"]].apply(pd.to_numeric, errors="coerce")
# the logger clock is UTC: its shortwave matches the 1725 m station's at no shift
a = a.resample("h").mean()
j = pd.concat([frc, a], axis=1).dropna()
T, U, P = j.AirTC_Avg.values, np.maximum(j.WS_ms_Avg.values, 0.1), j.P.values
es = lambda tc: 611.2 * np.exp(17.67 * tc / (tc + 243.5))  # noqa: E731
q = 0.622 * j.RH.values / 100 * es(T) / P
q0 = 0.622 * es(0.0) / P
rho = P / (287.0 * (T + 273.15))


def bulk(z0, stab, zu=2.3, zt=2.0, b=9.4, e=1.0):
    ustar = K * U / np.log(zu / z0)
    R = np.minimum(ustar * z0 / NU, 1000.0)
    lr = np.log(R)
    zh = np.where(R <= 0.135, z0 * np.exp(1.25), np.where(R < 2.5, z0 * np.exp(0.149 - 0.55 * lr),
                  z0 * np.exp(0.317 - 0.565 * lr - 0.183 * lr ** 2)))
    ch = K ** 2 / (np.log(zu / z0) * np.log(zt / zh))
    ri = 9.81 * zt * T / ((T + 273.15) * U ** 2)
    f = {"none": np.ones_like(ri), "louis": (1 + b / 2 * np.maximum(ri, 0)) ** -2.0,
         "mahrt": np.exp(-e * np.maximum(ri, 0)), "standard": np.where(ri < 0.2, (1 - 5 * np.maximum(ri, 0)) ** 2, 0)}[stab]
    f = np.where(ri < 0, (1 - 16 * ri) ** 0.75, f)
    return rho * CP * ch * f * U * T, rho * 2.834e6 * ch * f * U * (q - q0)


stake = pd.read_csv(os.path.join(C, "3_surface_height_change/gulkanaB_stake_2024.csv"), parse_dates=["Date"]).set_index("Date").CMB
for name, t0, t1, sfc in [("snow, isothermal", "2024-06-21", "2024-07-17", "snow"), ("ice", "2024-07-19", "2024-08-20", "ice")]:
    sel = (j.index >= t0) & (j.index < t1)
    days = (pd.Timestamp(t1) - pd.Timestamp(t0)).days
    melt = (stake.asof(pd.Timestamp(t0)) - stake.asof(pd.Timestamp(t1))) * 1000 * LF / (days * 86400)
    sw = (j.SWUpper_Avg - j.SWLower_Avg)[sel].mean()
    lw = (j.LWin[sel] - 315.6).mean()
    print(f"{name} {t0} to {t1}: melt {melt:.0f}, SWnet {sw:.0f}, LWnet {lw:.0f}, turbulent needed {melt - sw - lw:.0f} W m-2;"
          f" AWS T {T[sel].mean():.1f} C, U {U[sel].mean():.1f} m/s")
    z0s = [0.001, 0.005] if sfc == "ice" else [0.001]
    for z0 in z0s:
        for st in ["louis", "mahrt", "standard", "none"]:
            h, le = bulk(z0, st)
            print(f"   z0 {z0*1000:.0f} mm {st:8s}: H {h[sel].mean():5.1f}  LE {le[sel].mean():5.1f}  sum {(h + le)[sel].mean():5.1f}")
