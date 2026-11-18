#!/usr/bin/env python3
"""Numbers quoted for the round-3 best-trial figures (wolverine_best, gulkana_best) of glacier_forcing_runs.tex."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import numpy as np, pandas as pd
import plot_setup_runs as p

TRIALS = {"wolverine": [("added", "wolverine_added", 405), ("general", "wolverine_general", 452)],
          "gulkana": [("added", "gulkana_added", 467), ("general", "gulkana_general", 418)]}
TEMPS = {"wolverine": [("no lake", "wolverine_stream", "405_nolake"), ("lake", "wolverine_stream", "405_lake")],
         "gulkana": [("no fan", "gulkana_stream", "467_nowet"), ("fan", "gulkana_stream", "467_fan"), ("fan with flow", "gulkana_stream", "467_scale")]}
MONTHS = [5, 6, 7, 8, 9, 10]

for basin in TRIALS:
    folder, flow = p.OBS[basin]
    q = p.series(os.path.join(p.WORKFLOW, folder, flow), "q_obs")[p.START:p.END].dropna()
    print(f"===== {basin}: gauged days {len(q)}")
    cyc = q.groupby(q.index.day_of_year).mean().rolling(7, center=True).mean()
    print(f"gauge mean cycle peak doy {cyc.idxmax()} ({pd.Timestamp('2001-01-01') + pd.Timedelta(days=int(cyc.idxmax()) - 1):%d %b}), "
          f"first doy above 2 m3/s {cyc[cyc > 2].index.min()}")
    for label, case, s in TRIALS[basin]:
        d, ev = p.trial(case, "calibration_rerun", s)
        d = d.loc[q.index.intersection(d.index)]
        o = q.loc[d.index]
        c = d["Q"].groupby(d.index.day_of_year).mean().rolling(7, center=True).mean()
        vol = {m: d["Q"][d.index.month == m].sum() / o[o.index.month == m].sum() for m in MONTHS}
        ice = {m: d["Qice"][d.index.month == m].sum() / d["Q"][d.index.month == m].sum() for m in (6, 7, 8, 9)}
        print(f" {label} {s}: volume all {d['Q'].sum() / o.sum():.2f}; by month " + " ".join(f"{m}:{v:.2f}" for m, v in vol.items()))
        print(f"   peak doy {c.idxmax()} ({pd.Timestamp('2001-01-01') + pd.Timedelta(days=int(c.idxmax()) - 1):%d %b}), first doy above 2 m3/s {c[c > 2].index.min()}; "
              f"ice melt share JJAS " + " ".join(f"{m}:{v:.2f}" for m, v in ice.items()) +
              f"; JJA {d['Qice'][d.index.month.isin([6,7,8])].sum() / d['Q'][d.index.month.isin([6,7,8])].sum():.2f}")
        big = o.nlargest(3)
        print("   largest gauged days: " + ", ".join(f"{t:%Y-%m-%d} obs {v:.1f} sim {d['Q'][t]:.1f}" for t, v in big.items()))
    to = p.series(os.path.join(p.WORKFLOW, folder, p.TEMP[basin]), "t_obs").dropna()
    if to.max() > 200:
        to = to - 273.15
    print(" gauge water temperature monthly mean: " + " ".join(f"{m}:{to[to.index.month == m].mean():.2f}" for m in range(1, 13) if (to.index.month == m).any()))
    for label, case, suf in TEMPS[basin]:
        t = p.reach_temperature(case, "calibration_r3_rerun", suf).reindex(to.index)
        e = t - to
        print(f"  {label}: model " + " ".join(f"{m}:{t[t.index.month == m].mean():.2f}" for m in range(1, 13) if (to.index.month == m).any())
              + " | bias " + " ".join(f"{m}:{e[e.index.month == m].mean():+.2f}" for m in range(1, 13) if (to.index.month == m).any()))
