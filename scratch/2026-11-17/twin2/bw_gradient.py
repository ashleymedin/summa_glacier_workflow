#!/usr/bin/env python3
"""Winter-balance elevation gradient from the stakes alone, no forcing: in each year, the least-squares slope of
ln(bw) against stake elevation (stakes with bw > 0 above the terminus cutoff, years with 3 or more stakes). The median
over years is the glacier's exponential gradient b (/m), comparable to snow_ratio_form.py's b, but with the rain-snow
split folded in (rain at the low stakes steepens it).

    bw_gradient.py
"""
import os

import numpy as np
import pandas as pd

G = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
MIN_Z = {"Wolverine": 800.0, "Gulkana": 1300.0, "LemonCreek": 0.0}

for name, min_z in MIN_Z.items():
    s = pd.read_csv(os.path.join(G, f"data/domain_{name}/observations/storage/mass_balance/Input_{name}_Glaciological_Data.csv"))
    s = s[np.isfinite(s.bw) & (s.bw > 0) & (s.elevation >= min_z)]
    for lo, hi in ((1966, 2025), (2005, 2025)):
        b = []
        for _, y in s[(s.Year >= lo) & (s.Year <= hi)].groupby("Year"):
            if len(y) >= 3 and np.ptp(y.elevation) > 150:
                b.append(np.polyfit(y.elevation, np.log(y.bw), 1)[0])
        b = np.array(b)
        if len(b):
            print(f"{name:<10} {lo}-{hi}: {len(b):2d} years, stakes {s.elevation.min():.0f}-{s.elevation.max():.0f} m, "
                  f"b median {np.median(b):.5f} /m (IQR {np.percentile(b, 25):.5f}-{np.percentile(b, 75):.5f}), "
                  f"{100 * (np.exp(100 * np.median(b)) - 1):.0f} % per 100 m")
