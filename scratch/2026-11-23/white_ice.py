#!/usr/bin/env python3
"""Wolverine lake ice by water year on round-5b trial 465 (wolverine_stream, lake case): the peak black and white ice
of the cover, when its snow goes, when the ice goes and when the lake first passes 0.5 degC, against Sentinel-2's
openings (28 May-14 June, 2017-2026). Runs are on SUMMA white-ice; *_m1 without the lake's snowfall multiplier.
A path argument takes any rerun folder, e.g. a Stage B trial."""
import glob
import os
import sys

import netCDF4 as nc4
import numpy as np
import pandas as pd

W = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
RUNS = sys.argv[1:] or ["lake_wps_nrg", "lake_white", "lake_white_m1"]


def series(label):
    folder = label if os.sep in label else os.path.join(W, "runs/wolverine_stream/calibration_5b_rerun", f"sample_465_{label}")
    f = glob.glob(os.path.join(folder, "output", "*sample000001_day.nc"))[0]  # a label, or a rerun folder path
    with nc4.Dataset(f) as d:
        t = pd.DatetimeIndex(pd.Timestamp("1990-01-01") + pd.to_timedelta(np.round(d["time"][:].astype(float)), unit="s")).normalize()
        area = np.ma.filled(d["DOMarea_mean"][-1, 0, :].astype(float), 0)
        k = int(np.argmax(area * (np.arange(area.size) >= 3)))  # the lake: the largest wetland slot of HRU 1
        g = lambda v: pd.Series(np.ma.filled(d[v][:, 0, k].astype(float), np.nan), t) if v in d.variables else pd.Series(0.0, t)
        return pd.DataFrame({"ice": g("scalarLakeIceThick_mean"), "white": g("scalarLakeWhiteIceThick_mean"),
                             "swe": g("scalarSWE_mean"), "tw": g("scalarStreamTemp_mean") - 273.15})


first = lambda s: s.index[0].strftime("%m-%d") if len(s) else "-"
for label in RUNS:
    df = series(label)
    print(f"\n{label}\nWY   ice max  white max  snow out  ice out  >0.5C")
    for y in range(2007, 2027):
        w = df[f"{y - 1}-10-01":f"{y}-07-31"]
        spring = df[f"{y}-03-01":f"{y}-07-31"]
        print(f"{y} {w.ice.max():7.2f} {w.white.max():9.2f}   {first(spring.swe[spring.swe < 5])}    "
              f"{first(spring.ice[spring.ice < 0.01])}   {first(spring.tw[spring.tw > 0.5])}")
