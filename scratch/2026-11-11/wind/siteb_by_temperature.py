#!/usr/bin/env python3
"""Site B on-ice wind over the reference station's, split by the on-ice air temperature.

Asks whether the campaign can separate a sheltering factor (all temperatures) from a katabatic one (above 0 degC):
the ratio of mean winds [U_ice / U_1725] * [U_1725 / U_1480] in frozen and thawed hours, by month and overall, and
in 2 K bins of air temperature.  Same inputs and clock shift as wind_exposure_from_campaign.py.

    python scratch/2026-11-11/wind/siteb_by_temperature.py
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..", "..")
sys.path.insert(0, ROOT)
from wind_exposure_from_campaign import read_campaign, read_station  # noqa: E402

O = os.path.join(ROOT, "data", "domain_Gulkana", "observations")
camp = read_campaign(os.path.join(O, "campaigns/wilson_2024/1_meteo/gulkanaB_AWS_2024.csv"))
camp.index = camp.index + pd.Timedelta(hours=8)
bridge = os.path.join(O, "stations/1725/LVL2/gulkana1725_hourly_LVL2_*.csv")
ref = os.path.join(O, "stations/1480/LVL2/gulkana1480_hourly_LVL2_*.csv")
j = pd.concat([camp, read_station(bridge, set(camp.index.year)).rename("ub")], axis=1, sort=True).dropna()
yrs = set(range(2012, 2023))
k = pd.concat([read_station(bridge, yrs).rename("b"), read_station(ref, yrs).rename("r")], axis=1, sort=True).dropna()
link = k.b.groupby(k.index.month).mean() / k.r.groupby(k.index.month).mean()
j["ur"] = j.ub / j.index.month.map(link)  # reference-station wind implied by the bridge


def ratio(g):
    return g.u.mean() / g.ur.mean() if len(g) >= 48 else np.nan


print("month   frozen h  ratio   thawed h  ratio   thawed/frozen")
for m, g in j.groupby(j.index.month):
    f, t = g[g.t <= 0], g[g.t > 0]
    print(f"{m:5d} {len(f):9d} {ratio(f):6.2f} {len(t):10d} {ratio(t):6.2f} {ratio(t) / ratio(f):10.2f}")
f, t = j[j.t <= 0], j[j.t > 0]
print(f"  all {len(f):9d} {ratio(f):6.2f} {len(t):10d} {ratio(t):6.2f} {ratio(t) / ratio(f):10.2f}")
print("\nT bin (C)   hours  U_ice  U_ref  ratio")
for lo in range(-12, 14, 2):
    g = j[(j.t > lo) & (j.t <= lo + 2)]
    if len(g) >= 48:
        print(f"{lo:4d}..{lo + 2:<4d} {len(g):6d} {g.u.mean():6.2f} {g.ur.mean():6.2f} {ratio(g):6.2f}")
print("\nby hour-of-day class, thawed hours: ratio at night (22-06 local) vs day")
loc = (t.index.hour - 9) % 24
print(f"night {ratio(t[(loc >= 22) | (loc < 6)]):.2f}   day {ratio(t[(loc >= 6) & (loc < 22)]):.2f}")
