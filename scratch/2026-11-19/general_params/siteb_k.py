#!/usr/bin/env python3
"""Gulkana Site B 2024 air temperature against each forcing's (HRU 2), June-September hourly: Shaw et al.'s k (regression slope
with intercept, ambient above 0 C) beside our glacierTempReduction form (mean of the AWS over mean of the forcing above 0 C,
no intercept).

    siteb_k.py
"""
import glob
import os

import netCDF4 as nc
import numpy as np
import pandas as pd

WF = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
aws = pd.read_csv(f"{WF}/data/domain_Gulkana/observations/campaigns/wilson_2024/1_meteo/gulkanaB_AWS_2024.csv",
                  skiprows=[1, 2], parse_dates=["TIMESTAMP"], index_col="TIMESTAMP")
t = pd.to_numeric(aws.AirTC_Avg, errors="coerce").resample("h").mean()
for label, d in [("added", "data/domain_Gulkana/forcing/SUMMA_input/station_corrected"), ("general", "data/domain_Gulkana_general/forcing/SUMMA_input")]:
    parts = []
    for f in sorted(glob.glob(f"{WF}/{d}/*_2024??.nc")):
        with nc.Dataset(f) as x:
            tt = pd.to_datetime(nc.num2date(x["time"][:], x["time"].units, only_use_cftime_datetimes=False, only_use_python_datetimes=True)).round("h")
            parts.append(pd.Series(np.array(x["airtemp"][:, 1]) - 273.15, index=tt))
    j = pd.concat([t, pd.concat(parts)], axis=1, keys=["gla", "amb"]).dropna()
    j = j[j.index.month.isin([6, 7, 8, 9])]
    w = j[j.amb > 0]
    k, b = np.polyfit(w.amb, w.gla, 1)
    print(f"{label:8s} {len(w)} h: Shaw-style k {k:.2f} (intercept {b:+.2f} C); ratio of means above 0 C {w.gla.clip(lower=0).mean() / w.amb.mean():.2f}; "
          f"through-origin slope {np.sum(w.amb * w.gla) / np.sum(w.amb ** 2):.2f}")
