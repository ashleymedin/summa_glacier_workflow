#!/usr/bin/env python3
"""Site B on-ice air temperature against the 1725 m station's, lapsed to Site B (1682 m), April-August 2024.

Asks whether the cooling of air over the ice is a constant above 0 degC: the gap (off-ice minus on-ice) in 2 K bins
of the off-ice temperature, its mean in frozen and thawed hours, and a line through the thawed hours.

    python scratch/2026-11-11/wind/siteb_cooling.py
"""
import glob
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..", "..")
sys.path.insert(0, ROOT)
from wind_exposure_from_campaign import read_campaign  # noqa: E402

O = os.path.join(ROOT, "data", "domain_Gulkana", "observations")
LAPSE = {4: -6.4, 5: -7.1, 6: -7.3, 7: -7.8, 8: -7.8}  # stations' monthly lapse rate (K/km)
camp = read_campaign(os.path.join(O, "campaigns/wilson_2024/1_meteo/gulkanaB_AWS_2024.csv"))
camp.index = camp.index + pd.Timedelta(hours=8)
d = pd.concat(pd.read_csv(f, usecols=["UTC_time", "site_temp_USGS"])
              for f in glob.glob(os.path.join(O, "stations/1725/LVL2/gulkana1725_hourly_LVL2_202[34].csv")))
s = d.set_index(pd.to_datetime(d.UTC_time))[["site_temp_USGS"]].astype(float)
s = s[~s.index.duplicated()]
j = pd.concat([camp, s], axis=1, sort=True).dropna(subset=["t", "site_temp_USGS"])
j["off"] = j.site_temp_USGS + j.index.month.map(LAPSE) * 1e-3 * (1682 - 1725)
j["gap"] = j.off - j.t

print("off-ice T (C)  hours  gap (K)  on-ice wind (m/s)")
for lo in range(-10, 16, 2):
    g = j[(j.off > lo) & (j.off <= lo + 2)]
    if len(g) >= 48:
        print(f"{lo:5d}..{lo + 2:<5d} {len(g):6d} {g.gap.mean():7.2f} {g.u.mean():10.2f}")
f, t = j[j.off <= 0], j[j.off > 0]
print(f"\nfrozen hours {len(f)}: gap {f.gap.mean():.2f} K;  thawed hours {len(t)}: gap {t.gap.mean():.2f} K")
jja = t[t.index.month >= 6]
print(f"June-August thawed hours {len(jja)}: gap {jja.gap.mean():.2f} K")
c = np.polyfit(t.off, t.gap, 1)
print(f"thawed hours: gap = {c[0]:.3f} * T_off {c[1]:+.2f}  (rms about the line {np.std(t.gap - np.polyval(c, t.off)):.2f} K, "
      f"about the constant {t.gap.std():.2f} K)")
# positive-degree weight: the constant that gives the same sum of on-ice positive degrees
w = (t.off.clip(lower=0).sum() - t.t.clip(lower=0).sum()) / len(t)
print(f"mean loss of positive degrees over thawed hours {w:.2f} K")
for name, g in (("day", t[(t.index.hour - 9) % 24 // 6 % 3 > 0]), ("night", t[((t.index.hour - 9) % 24 < 6)])):
    print(f"{name}: gap {g.gap.mean():.2f} K over {len(g)} h")
