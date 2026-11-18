#!/usr/bin/env python3
"""The delta row of the wetland table (tab:wetland), scored as lake_heat.py scores its runs: trial 405 on
wolverine_stream_delta, the lake (HRU 1, domain 4) below the braided delta.

    ./lake_heat_delta_row.py
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "2026-11-13"))
import numpy as np, pandas as pd
import lake_heat as lh

W = os.path.join(HERE, "..", "..")
obs = os.path.join(W, "data/domain_Wolverine/observations/calibration")
tobs = lh.obs_series(os.path.join(obs, "USGS_15236900_daily_temperature.nc"), "t_obs")
qobs = lh.obs_series(os.path.join(obs, "USGS_15236900_daily_flow.nc"), "q_obs")
if tobs.max() > 200:
    tobs = tobs - 273.15
day, wet = lh.load(os.path.join(W, "runs/wolverine_stream_delta/calibration_r3_rerun"), "delta")
e = (day["T"] - 273.15).reindex(tobs.index).sub(tobs).dropna()
q = pd.concat([day["Q"].reindex(qobs.index), qobs], axis=1, keys=["s", "o"]).dropna()[lh.EVAL[0]:lh.EVAL[1]]
month = e.groupby(e.index.month).mean().reindex(lh.MONTHS)
summer = wet[wet.index.month.isin([6, 7, 8, 9]) & (wet.area > 0)]
heat = lh.RHOC * summer.qout * (summer.Tw - 273.15)
print(f"KGE {lh.kge(q.s, q.o):.3f} T RMSE cal {np.sqrt((e[lh.CAL[0]:lh.CAL[1]]**2).mean()):.2f} "
      f"eval {np.sqrt((e[lh.EVAL[0]:lh.EVAL[1]]**2).mean()):.2f} monthly " + " ".join(f"{m}:{v:+.2f}" for m, v in month.items()))
print(f"JJAS lake heat {heat.mean()/1e6:.2f} MW, warming {np.nanmean(heat/(lh.RHOC*day['Q'].reindex(summer.index, method='nearest'))):.2f} K")
_, delta = lh.load(os.path.join(W, "runs/wolverine_stream_delta/calibration_r3_rerun"), "delta", wet=(0, 4))
ds = delta[delta.index.month.isin([6, 7, 8, 9]) & (delta.area > 0)]
dheat = lh.RHOC * ds.qout * (ds.Tw - 273.15)
print(f"JJAS delta {ds.Tw.mean() - 273.15:.2f} C, heat {dheat.mean()/1e6:.2f} MW, area {ds.area.median()/1e6:.4f} km2; "
      f"lake {summer.Tw.mean() - 273.15:.2f} C")
