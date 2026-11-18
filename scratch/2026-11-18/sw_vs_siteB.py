#!/usr/bin/env python3
"""Incoming shortwave of the forcing (HRU nearest 1682 m) against Gulkana Site B's 2024 AWS (Wilson et al.), daily means.

    sw_vs_siteB.py
"""
import glob
import os

import netCDF4 as nc
import numpy as np
import pandas as pd

WF = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
aws = pd.read_csv(f"{WF}/data/domain_Gulkana/observations/campaigns/wilson_2024/1_meteo/gulkanaB_AWS_2024.csv",
                  skiprows=[1, 2], parse_dates=["TIMESTAMP"], index_col="TIMESTAMP")
sw = pd.to_numeric(aws.SWUpper_Avg, errors="coerce")
obs = sw.resample("D").mean()[sw.resample("D").count() >= 0.9 * sw.resample("D").count().max()]
for label, d in [("added", "data/domain_Gulkana/forcing/SUMMA_input/station_corrected"), ("general", "data/domain_Gulkana_general/forcing/SUMMA_input"),
                 ("ERA5", "data/domain_Gulkana/forcing/SUMMA_input")]:
    parts = []
    for f in sorted(glob.glob(f"{WF}/{d}/*_2024??.nc")):
        with nc.Dataset(f) as s:
            t = pd.to_datetime(nc.num2date(s["time"][:], s["time"].units, only_use_cftime_datetimes=False, only_use_python_datetimes=True))
            parts.append(pd.Series(np.array(s["SWRadAtm"][:, 1]), index=t))
    f = pd.concat(parts).resample("D").mean()
    j = pd.concat([obs, f], axis=1, keys=["obs", "frc"]).dropna()
    for name, m in [("May-Sep", j.index.month.isin(range(5, 10))), ("JJA", j.index.month.isin([6, 7, 8]))]:
        x = j[m]
        print(f"{label:8s} {name}: {len(x)} days, AWS {x.obs.mean():.0f}, forcing {x.frc.mean():.0f} W m-2 (ratio {x.frc.mean() / x.obs.mean():.2f}), "
              f"r {x.obs.corr(x.frc):.2f}, sd AWS {x.obs.std():.0f} forcing {x.frc.std():.0f}")
