#!/usr/bin/env python3
"""An experiment's 2024 summer on Gulkana's clean-glacier domains against the Site B campaign: monthly albedo and
energy terms of HRU 2, and cumulative balance at the B, AB and D stakes (HRU by nearest domain elevation).

    siteb_run.py base [other experiments]
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exp import GLACIER, load, mass_series  # noqa: E402

C = os.path.join(GLACIER, "data/domain_Gulkana/observations/campaigns/wilson_2024")
alb = pd.read_csv(os.path.join(C, "5_albedo/gulkanaB_daily_albedo_2024.csv"), parse_dates=["date"]).set_index("date").albedo
z = {"AB": 1541, "B": 1682, "D": 1843}
for name in sys.argv[1:]:
    v, time, dom = load("gulkana_added", name)
    sel = (time >= "2024-04-17") & (time <= "2024-09-15")
    h, m = 1, dom[1]
    df = pd.DataFrame({"SWnet": v["scalarGroundAbsorbedSolar"][sel, h, m], "SWin": v["SWRadAtm"][sel, h],
                       "LWnet": v["scalarLWNetGround"][sel, h, m], "H": v["scalarSenHeatGround"][sel, h, m],
                       "LE": v["scalarLatHeatGround"][sel, h, m], "SWE": v["scalarSWE"][sel, h, m]}, index=time[sel])
    g = df.groupby(df.index.month)
    o = g.mean()
    o["alb_sim"] = 1 - g.SWnet.sum() / g.SWin.sum()
    o["alb_obs"] = alb.groupby(alb.index.month).mean()
    print(f"== {name}: HRU 2 clean glacier, 2024")
    print(o.round(2).to_string())
    series = mass_series(v, time, dom)
    for site, zs in z.items():
        obs = pd.read_csv(os.path.join(C, f"3_surface_height_change/gulkana{site}_stake_2024.csv"), parse_dates=["Date"]).set_index("Date").CMB
        hh = min(series, key=lambda k: abs(series[k][1] - zs))
        s = series[hh][0]
        t0, t1 = obs.index[0], obs.dropna().index[-1]
        print(f"  {site} ({zs} m, HRU {hh + 1}): {t0.date()} to {t1.date()} obs {obs.dropna().iloc[-1]:.2f}, sim {s.asof(t1) - s.asof(t0):.2f} m w.e.")
