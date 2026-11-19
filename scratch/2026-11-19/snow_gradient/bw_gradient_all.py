#!/usr/bin/env python3
"""Winter-balance elevation gradient of every USGS glacier with stakes, against glacier size: each year's least-squares slope of
ln(bw) on stake elevation (stakes with bw > 0, years with 3 or more stakes spanning over 150 m), median over the years.

    bw_gradient_all.py
"""
import os

import numpy as np
import pandas as pd

WF = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
EXT = f"{WF}/data/external/USGS_massBalance"
FILES = {"Wolverine": f"{WF}/data/domain_Wolverine/observations/storage/mass_balance",
         "Gulkana": f"{WF}/data/domain_Gulkana/observations/storage/mass_balance",
         "LemonCreek": f"{WF}/data/domain_LemonCreek/observations/storage/mass_balance",
         **{g: f"{EXT}/{g}" for g in ("Taku", "Kennicott", "Kahiltna", "SouthCascade", "Sperry")}}
RGI7 = {"Wolverine": "Wolverine Glacier", "Gulkana": "Gulkana Glacier", "LemonCreek": "Lemon Creek Glacier", "Taku": "Taku Glacier",
        "Kennicott": "Kennicott Glacier", "Kahiltna": "Kahiltna Glacier"}
attrs = pd.read_csv(f"{WF}/data/external/RGI_data/RGI2000-v7.0-G-global/RGI2000-v7.0-G-01_alaska/RGI2000-v7.0-G-01_alaska-attributes.csv")


def area(name):
    if name in RGI7:
        a = attrs[attrs.glac_name.fillna("").str.lower() == RGI7[name].lower()]
        return a.area_km2.max() if len(a) else np.nan
    h = pd.read_csv(f"{FILES[name]}/Input_{name}_Area_Altitude_Distribution.csv")
    return h.iloc[-1, 1:].astype(float).sum()


def slopes(s, lo=1966, hi=2025):
    b = []
    for _, y in s[(s.Year >= lo) & (s.Year <= hi)].groupby("Year"):
        if len(y) >= 3 and np.ptp(y.elevation) > 150:
            b.append(np.polyfit(y.elevation, np.log(y.bw), 1)[0])
    return np.array(b)


rows = []
for name, d in FILES.items():
    s = pd.read_csv(f"{d}/Input_{name}_Glaciological_Data.csv")
    s = s[np.isfinite(s.bw) & (s.bw > 0)]
    for lo in (1966, 2000):
        b = slopes(s, lo)
        if len(b):
            rows.append(dict(glacier=name, area_km2=round(area(name), 1), since=lo, years=len(b), stakes_m=f"{s.elevation.min():.0f}-{s.elevation.max():.0f}",
                             mean_bw=round(s[s.Year >= lo].bw.mean(), 2), b_median=round(np.median(b), 5),
                             b_iqr=f"{np.percentile(b, 25):.5f}-{np.percentile(b, 75):.5f}"))
t = pd.DataFrame(rows)
print(t.to_string(index=False))
