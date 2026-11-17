#!/usr/bin/env python3
"""Mean annual rainfall, snowfall and glacier melt over the basin (mm/yr) of reruns, by domain type, WY2006-2015.

    water_budget.py runs/wolverine_added/calibration_rerun/sample_472 runs/wolverine_added/calibration_rerun_oldforcing/sample_391
"""
import glob
import sys

import netCDF4 as nc
import numpy as np
import pandas as pd

for run in sys.argv[1:]:
    f = sorted(glob.glob(f"{run}/output/*_sample*_day.nc"))[0]
    with nc.Dataset(f) as d:
        t = pd.to_datetime(nc.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False))
        sel = (t >= "2005-10-01") & (t < "2015-10-01")
        area = np.ma.filled(d["DOMarea_mean"][sel].astype(float), 0)  # m2, time x dom x hru
        typ = np.ma.filled(d["domType"][:].astype(int), -1)
        tot = area[0].sum()
        out = {}
        for v in ("scalarRainfall_mean", "scalarSnowfall_mean", "scalarGlacierMelt_mean"):
            x = np.ma.filled(d[v][sel].astype(float), 0) * 86400  # kg m-2 s-1 to mm/day
            for k in np.unique(typ[typ >= 0]):
                m = (typ == k)
                out[(v.split("_")[0].replace("scalar", ""), int(k))] = (x * area * m).sum() / tot / 10
    print(run)
    for (v, k), x in sorted(out.items()):
        print(f"  dom type {k}  {v:12s} {x:7.0f} mm/yr over the basin")
