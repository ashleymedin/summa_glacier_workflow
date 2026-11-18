#!/usr/bin/env python3
"""Snowfall and rainfall on each HRU's glacier domain from 1 June to 15 September in a rerun, and their regression on the summer's
forcing degree-days: how much of the simulated summer-balance sensitivity is summer snowfall turning to rain.

    summer_snow.py wolverine_added:405_aligned:990
"""
import glob
import sys

import netCDF4 as nc
import numpy as np
import pandas as pd

from summer_forcing_vs_station import WF, forcing

for spec in sys.argv[1:]:
    case, run, elev = spec.split(":")
    fo, _ = forcing(case, int(elev))
    f = [p for p in glob.glob(f"{WF}/runs/{case}/calibration_rerun/sample_{run}/output/*_day.nc") if "spinup" not in p][0]
    with nc.Dataset(f) as d:
        t = pd.to_datetime(nc.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False, only_use_python_datetimes=True))
        typ = np.ma.filled(d["domType"][:].astype(int), -1)
        sn = np.ma.filled(d["scalarSnowfall_mean"][:].astype(float), np.nan) * 86400
        ra = np.ma.filled(d["scalarRainfall_mean"][:].astype(float), np.nan) * 86400
    print(f"== {case} {run}: glacier-domain summer (Jun 1 - Sep 15) snowfall and rain, mm w.e.")
    for h in range(typ.shape[0]):
        m = int(np.argmax(typ[h] == 2))
        df = pd.DataFrame({"snow": sn[:, h, m], "rain": ra[:, h, m]}, index=t)
        df = df[((df.index.month >= 6) & (df.index.month <= 8)) | ((df.index.month == 9) & (df.index.day <= 15))]
        y = df.groupby(df.index.year).sum()
        y = y[(y.index >= 2006) & (y.index <= 2025)]
        pdd = fo["T"][fo["T"].index.month.isin([6, 7, 8])].clip(lower=0).groupby(fo["T"][fo["T"].index.month.isin([6, 7, 8])].index.year).sum().reindex(y.index)
        print(f"  HRU {h + 1}: snow {y.snow.mean():.0f} (per JJA degree-day {np.polyfit(pdd, y.snow, 1)[0]:+.2f}), "
              f"rain {y.rain.mean():.0f} ({np.polyfit(pdd, y.rain, 1)[0]:+.2f})")
