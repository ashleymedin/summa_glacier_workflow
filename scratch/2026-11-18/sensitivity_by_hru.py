#!/usr/bin/env python3
"""Summer balance per positive degree-day at each HRU's stakes, observed and simulated, against the forcing's degree-days and the
station's (stake spring to fall dates), for reruns of calibration_rerun/sample_<run>.

    sensitivity_by_hru.py wolverine_added:405_aligned:990 gulkana_added:467_aligned:1480
"""
import sys

import numpy as np
import pandas as pd

import stakes_by_hru as s
from summer_forcing_vs_station import forcing, station

for spec in sys.argv[1:]:
    case, run, elev = spec.split(":")
    basin = case.split("_")[0]
    series, grad = s.domain_mass(case, run)
    name = s.STAKES[basin]
    csv = f"{s.WF}/data/domain_{name}/observations/storage/mass_balance/Input_{name}_Glaciological_Data.csv"
    st = pd.read_csv(csv, parse_dates=["spring_date", "fall_date"]).dropna(subset=["spring_date", "fall_date", "ba", "bw"])
    st = st[(st.Year >= 2006) & (st.Year <= 2025)]
    fo, _ = forcing(case, int(elev))
    stn = station(basin, int(elev))
    rows = []
    for _, r in st.iterrows():
        h = min(series, key=lambda k: abs(series[k][1] - r.elevation))
        m, z = series[h]
        if r.fall_date > m.index[-1]:
            continue
        w = slice(r.spring_date.normalize(), r.fall_date.normalize())
        n = len(fo["T"].loc[w])
        rows.append(dict(hru=h + 1, bs_obs=r.ba - r.bw, bs_sim=float(m.asof(r.fall_date)) - float(m.asof(r.spring_date)),
                         pdd=fo["T"].loc[w].clip(lower=0).sum(),
                         pdd_st=stn["T"].loc[w].clip(lower=0).sum() if stn["T"].loc[w].notna().sum() > 0.9 * n else np.nan))
    t = pd.DataFrame(rows)
    print(f"== {case} {run}: summer balance per degree-day (mm w.e.)")
    for h, g in t.groupby("hru"):
        g2 = g.dropna()
        sl = lambda x, y: np.polyfit(x, y, 1)[0] * 1000  # noqa: E731
        print(f"  HRU {h}: forcing PDD (n {len(g)}) obs {sl(g.pdd, g.bs_obs):.2f} sim {sl(g.pdd, g.bs_sim):.2f};"
              f" station PDD (n {len(g2)}) obs {sl(g2.pdd_st, g2.bs_obs):.2f} sim {sl(g2.pdd_st, g2.bs_sim):.2f}")
