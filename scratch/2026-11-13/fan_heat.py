#!/usr/bin/env python3
"""Does Gulkana's braided fan add heat? Trial 451 of the added-data calibration rerun on the stream case
(fan_heat_runs.sh): no wetland, the fan as built and the whole fan wet. Prints discharge KGE, the 2006
water-temperature error by month (the gauge's only record, Feb-Aug 2006) and the heat the fan adds.

    ./fan_heat.py RUNS_DIR OBS_DIR
      RUNS_DIR  runs/gulkana_stream/calibration_added_rerun
      OBS_DIR   data/domain_Gulkana/observations/calibration
"""
import os
import sys

import numpy as np
import pandas as pd

from lake_heat import RHOC, kge, load, obs_series

RUNS = [("nowet", "no wetland"), ("fan", "fan 0.056 km2"), ("wide", "fan 0.21 km2")]
EVAL = ("2019-10-01", "2026-09-30")
T06 = ("2006-06-01", "2006-08-31")


def main():
    runs_dir, obs_dir = sys.argv[1:3]
    tobs = obs_series(os.path.join(obs_dir, "USGS_15478040_daily_temperature.nc"), "t_obs")
    qobs = obs_series(os.path.join(obs_dir, "USGS_15478040_daily_flow.nc"), "q_obs")
    if tobs.max() > 200:
        tobs = tobs - 273.15
    print(f"gauge Jun-Aug 2006 mean {tobs[T06[0]:T06[1]].mean():.2f} C")
    for label, name in RUNS:
        day, wet = load(runs_dir, label, wet=(0, 3))
        T = day["T"] - 273.15
        e = (T.reindex(tobs.index) - tobs).dropna()
        q = pd.concat([day["Q"].reindex(qobs.index), qobs], axis=1, keys=["s", "o"]).dropna()
        qe = q[EVAL[0]:EVAL[1]]
        js = e[T06[0]:T06[1]]
        month = e.groupby(e.index.month).mean()
        print(f"{name:16s} KGE eval {kge(qe.s, qe.o):.3f}  2006 Jun-Aug T RMSE {np.sqrt((js ** 2).mean()):.2f} K, "
              f"bias {js.mean():+.2f} K, model mean {T[T06[0]:T06[1]].mean():.2f} C  monthly "
              + " ".join(f"{m}:{v:+.2f}" for m, v in month.items()))
        summer = wet[wet.index.month.isin([6, 7, 8, 9]) & (wet.area > 0)]
        if len(summer):
            heat = RHOC * summer.qout * (summer.Tw - 273.15)
            gauge = day["Q"].reindex(summer.index, method="nearest")
            print(f"{'':16s} JJAS fan {summer.Tw.mean() - 273.15:.2f} C, heat {heat.mean() / 1e6:.2f} MW, "
                  f"warming the gauge flow {np.nanmean(heat / (RHOC * gauge)):.2f} K; JJAS gauge water "
                  f"{(day['T'][day.index.month.isin([6, 7, 8, 9])] - 273.15).mean():.2f} C")


if __name__ == "__main__":
    main()
