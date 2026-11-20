#!/usr/bin/env python3
"""Stage 0 of Paper 2: round-5b trial 465 on the Wolverine stream cases, scored as lake_heat.py scores its runs, beside
round-3 trial 405: water-temperature RMSE and mean error by month, the first spring day the lake is above 0.5 degC (against
Sentinel-2's openings, early to mid June 2017-2026) and the most snow on it before June.
The *_wetprecip runs are on SUMMA wetland-precip (d1bfe962), where the lake takes its HRU's precipitation; *_wpsnow
also give the lake the upland's snowfall multiplier (frozenPrecipMultip@wetland)."""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "2026-11-13"))
import netCDF4 as nc4
import numpy as np
import pandas as pd
import lake_heat as lh

W = os.path.join(HERE, "..", "..")
obs = os.path.join(W, "data/domain_Wolverine/observations/calibration")
tobs = lh.obs_series(os.path.join(obs, "USGS_15236900_daily_temperature.nc"), "t_obs")
tobs = tobs - 273.15 if tobs.max() > 200 else tobs
RUNS = [("r3 405 nolake", "wolverine_stream/calibration_r3_rerun", "nolake"),
        ("r3 405 delta", "wolverine_stream_delta/calibration_r3_rerun", "delta"),
        ("5b 465 nolake", "wolverine_stream/calibration_5b_rerun", "nolake"),
        ("5b 465 lake", "wolverine_stream/calibration_5b_rerun", "lake"),
        ("5b 465 delta", "wolverine_stream_delta/calibration_5b_rerun", "delta"),
        ("5b 465 lake wp", "wolverine_stream/calibration_5b_rerun", "lake_wetprecip"),
        ("5b 465 delta wp", "wolverine_stream_delta/calibration_5b_rerun", "delta_wetprecip"),
        ("5b 465 lake wps", "wolverine_stream/calibration_5b_rerun", "lake_wpsnow"),
        ("5b 465 delta wps", "wolverine_stream_delta/calibration_5b_rerun", "delta_wpsnow")]


def lake_snow(folder, label):
    """The lake domain's SWE (mm): of HRU 1's wetland slots, the one with the largest area at the end of the run."""
    files = glob.glob(os.path.join(W, "runs", folder, f"sample_*_{label}", "output", "*sample000001_day.nc"))
    with nc4.Dataset(files[0]) as d:
        t = pd.Timestamp("1990-01-01") + pd.to_timedelta(np.round(np.array(d["time"][:], float)), unit="s")
        area = np.ma.filled(d["DOMarea_mean"][-1, 0, :].astype(float), 0)
        dom = int(np.argmax(area * (np.arange(area.size) >= 3)))
        return pd.Series(np.ma.filled(d["scalarSWE_mean"][:, 0, dom].astype(float), np.nan), index=t)


for name, folder, label in RUNS:
    if not glob.glob(os.path.join(W, "runs", folder, f"sample_*_{label}")):
        continue
    day, wet = lh.load(os.path.join(W, "runs", folder), label)
    e = (day["T"] - 273.15).reindex(tobs.index).sub(tobs).dropna()
    month = e.groupby(e.index.month).mean().reindex(lh.MONTHS)
    print(f"{name:16s} cal {np.sqrt((e[lh.CAL[0]:lh.CAL[1]]**2).mean()):.2f} eval {np.sqrt((e[lh.EVAL[0]:lh.EVAL[1]]**2).mean()):.2f} "
          + " ".join(f"{m}:{v:+.2f}" for m, v in month.items()))
    if len(wet) and wet.area.max() > 0:
        tw, swe = wet.Tw - 273.15, lake_snow(folder, label)
        opens = []
        for y in range(2016, 2027):
            s = tw[f"{y}-03-01":f"{y}-07-31"]
            w = s[s > 0.5].index
            opens.append(f"{y % 100}:{w[0]:%m-%d}/{swe[f'{y}-01-01':f'{y}-05-31'].max():.0f}" if len(w) else f"{y % 100}:-")
        print("   lake >0.5 C / snow mm  " + " ".join(opens))
