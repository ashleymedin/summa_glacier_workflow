#!/usr/bin/env python3
"""A tab:lakeice row for each stream_cheap_r9 rerun of trial 79 (labels as arguments, default as_found and no_wind_air):
peak lake ice and the lake's opening (first spring day above 0.5 degC) over 2017-2026, water-temperature RMSE over
WY2016-19 and WY2020-26, and the mean error by month, May-October 2016-2026, as stage0_months.py and white_ice.py score them."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "2026-11-13"))
import glob

import netCDF4 as nc4
import numpy as np
import pandas as pd
import lake_heat as lh

labels = sys.argv[1:] or ["as_found", "no_wind_air"]


def lake_ice(folder):
    """The lake's ice thickness (m), white_ice.py's series: HRU 1's largest wetland slot at the end of the run."""
    with nc4.Dataset(glob.glob(os.path.join(folder, "output", "*sample000001_day.nc"))[0]) as d:
        area = np.ma.filled(d["DOMarea_mean"][-1, 0, :].astype(float), 0)
        k = int(np.argmax(area * (np.arange(area.size) >= 3)))
        return pd.Series(np.ma.filled(d["scalarLakeIceThick_mean"][:, 0, k].astype(float), np.nan), lh.times(d).normalize()), k

W = os.path.join(HERE, "..", "..", "..")
RERUN = os.path.join(W, "runs/wolverine_stream_delta/stream_cheap_r9_rerun")
obs = os.path.join(W, "data/domain_Wolverine/observations/calibration")
tobs = lh.obs_series(os.path.join(obs, "USGS_15236900_daily_temperature.nc"), "t_obs")
tobs = tobs - 273.15 if tobs.max() > 200 else tobs

for label in labels:
    day, wet = lh.load(RERUN, label)
    e = (day["T"] - 273.15).reindex(tobs.index).sub(tobs).dropna()
    month = e["2015-10-01":"2026-09-30"].groupby(e["2015-10-01":"2026-09-30"].index.month).mean().reindex(lh.MONTHS)
    ice, k = lake_ice(os.path.join(RERUN, f"sample_79_{label}"))
    peaks = [ice[f"{y - 1}-10-01":f"{y}-07-31"].max() for y in range(2017, 2027)]
    opens = []
    for y in range(2017, 2027):
        s = (wet.Tw - 273.15)[f"{y}-03-01":f"{y}-07-31"]
        w = s[s > 0.5].index
        opens.append(w[0] if len(w) else None)
    shut = [y for y, o in zip(range(2017, 2027), opens) if o is None]
    o = sorted((x.replace(year=2000) for x in opens if x is not None))
    rmse = lambda a, b: np.sqrt((e[a:b] ** 2).mean())
    print(f"{label}: peak {min(peaks):.1f}--{max(peaks):.1f} m, open {o[0]:%-d %b}--{o[-1]:%-d %b}"
          + (f" (shut {shut})" if shut else "") + f", RMSE {rmse(*lh.CAL):.2f} {rmse(*lh.EVAL):.2f}, "
          + " ".join(f"{m}:{v:+.2f}" for m, v in month.items()))
    print("   opens " + " ".join(f"{y % 100}:{x:%m-%d}" if x is not None else f"{y % 100}:-" for y, x in zip(range(2017, 2027), opens))
          + f"   peaks (slot {k}) " + " ".join(f"{p:.2f}" for p in peaks))
