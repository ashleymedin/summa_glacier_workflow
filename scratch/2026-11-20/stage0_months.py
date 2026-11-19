#!/usr/bin/env python3
"""Stage 0 of Paper 2: round-5b trial 465 on the Wolverine stream cases, scored as lake_heat.py scores its runs, beside
round-3 trial 405: water-temperature RMSE and mean error by month, and the lake's July-August area."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "2026-11-13"))
import numpy as np
import lake_heat as lh

W = os.path.join(HERE, "..", "..")
obs = os.path.join(W, "data/domain_Wolverine/observations/calibration")
tobs = lh.obs_series(os.path.join(obs, "USGS_15236900_daily_temperature.nc"), "t_obs")
tobs = tobs - 273.15 if tobs.max() > 200 else tobs
RUNS = [("r3 405 nolake", "wolverine_stream/calibration_r3_rerun", "nolake"),
        ("r3 405 delta", "wolverine_stream_delta/calibration_r3_rerun", "delta"),
        ("5b 465 nolake", "wolverine_stream/calibration_5b_rerun", "nolake"),
        ("5b 465 lake", "wolverine_stream/calibration_5b_rerun", "lake"),
        ("5b 465 delta", "wolverine_stream_delta/calibration_5b_rerun", "delta")]
for name, folder, label in RUNS:
    day, wet = lh.load(os.path.join(W, "runs", folder), label)
    e = (day["T"] - 273.15).reindex(tobs.index).sub(tobs).dropna()
    month = e.groupby(e.index.month).mean().reindex(lh.MONTHS)
    ja = wet[wet.index.month.isin([7, 8])].area.groupby(wet[wet.index.month.isin([7, 8])].index.year).median() / 1e6 if len(wet) else None
    print(f"{name:15s} cal {np.sqrt((e[lh.CAL[0]:lh.CAL[1]]**2).mean()):.2f} eval {np.sqrt((e[lh.EVAL[0]:lh.EVAL[1]]**2).mean()):.2f} "
          + " ".join(f"{m}:{v:+.2f}" for m, v in month.items()))
    if ja is not None:
        print("   lake Jul-Aug km2 " + " ".join(f"{y % 100:02d}:{a:.3f}" for y, a in ja.items() if y >= 2010))
