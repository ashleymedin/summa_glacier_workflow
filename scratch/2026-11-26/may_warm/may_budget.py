#!/usr/bin/env python3
"""Where trial 79's warm May comes from (diag.sh rerun): by month over 2016-2026, the gauge against USGS, the lake outflow,
the reach's lateral inflow (GRU runoff, groundwater and lake) and its temperature, the aquifer baseflow, the friction
warming g*drop/cp of the reach, and the reach's ice and snow."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "2026-11-13"))
import glob

import netCDF4 as nc4
import numpy as np
import pandas as pd
import lake_heat as lh

W = os.path.join(HERE, "..", "..", "..")
R = os.path.join(W, "runs/wolverine_stream_delta/stream_cheap_r9_rerun")
LAKE, REACH = (0, 3), (3, 1)  # (HRU, domain) indices
tobs = lh.obs_series(os.path.join(W, "data/domain_Wolverine/observations/calibration/USGS_15236900_daily_temperature.nc"), "t_obs")
tobs = tobs - 273.15 if tobs.max() > 200 else tobs
day, _ = lh.load(R, "diag")
with nc4.Dataset(glob.glob(os.path.join(R, "sample_79_diag/output/*sample000001_day.nc"))[0]) as d:
    t = lh.times(d)
    g = lambda v, *ix: pd.Series(np.ma.filled(np.asarray(d[v][(slice(None),) + ix], float), np.nan), t)
    area = np.ma.filled(d["DOMarea_mean"][-1], 0)
    reach_area = area[REACH]
    df = pd.DataFrame({"Tlake": g("scalarStreamTemp_mean", *LAKE) - 273.15, "qlake": g("scalarStreamOutflow_mean", *LAKE),
                       "base": g("basin__AquiferBaseflow_mean", 0) * area[area > 0].sum(),
                       "qlat": g("scalarStreamLatInflow_mean", *REACH), "Tlat": g("scalarStreamLatInflowTemp_mean", *REACH) - 273.15,
                       "Treach": g("scalarStreamTemp_mean", *REACH) - 273.15,
                       "dTfric": g("scalarStreamFrictionHeat_mean", *REACH) * reach_area / (4.18e6 * g("scalarStreamOutflow_mean", *REACH)),
                       "ice": g("scalarLakeIceThick_mean", *REACH), "swe": g("scalarSWE_mean", *REACH)})
f = df[df.index.year >= 2016]
out = f.groupby(f.index.month).mean()
o = tobs[tobs.index.year >= 2016]
out["obs"] = o.groupby(o.index.month).mean()
out["gauge"] = (day["T"] - 273.15).reindex(o.index).groupby(o.index.month).mean()
pd.set_option("display.width", 200)
print(out[["obs", "gauge", "Treach", "Tlat", "Tlake", "qlake", "base", "qlat", "dTfric", "ice", "swe"]].round(2).loc[[3, 4, 5, 6, 7, 8, 9, 10]])
