#!/usr/bin/env python3
"""Cheap trial 87 under each deep thermal option (onoff.sh): discharge KGE and water-temperature RMSE at the gauge, the
monthly means there, and the basin's yearly water balance (mm: precipitation, ET, surface runoff, baseflow, the aquifer at
each water year's end).

    onoff_score.py bedrock none airgw
"""
import os
import sys

import netCDF4 as nc4
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slate_default import HERE, reach_scores  # noqa: E402

S = 86400 * 1000  # m s-1 to mm day-1


def balance(work):
    f = [x for x in os.listdir(os.path.join(work, "output")) if x.endswith("_day.nc") and "spinup" not in x][0]
    with nc4.Dataset(os.path.join(work, "output", f)) as d:
        d.set_auto_mask(False)
        t = pd.to_datetime(nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False))
        area = d["DOMarea_mean"][0, :, 0]
        hru_area = np.where(area > 0, area, 0)
        w = hru_area / hru_area.sum()
        gru_of = d["gruId"][:]
        p = ((d["scalarRainfall_mean"][:, :, 0] + d["scalarSnowfall_mean"][:, :, 0]) * w).sum(1) * 86400
        et = (d["scalarTotalET_mean"][:, :, 0] * w).sum(1) * 86400
        aq = (np.where(d["scalarAquiferStorage_mean"][:, :, 0] > -1, d["scalarAquiferStorage_mean"][:, :, 0], 0) * w).sum(1) * 1000
        n_gru = len(gru_of)
        gw = hru_area.reshape(n_gru, -1).sum(1) / hru_area.sum()  # the output holds each GRU's HRUs together
        qs = (np.where(np.abs(d["basin__SurfaceRunoff_mean"][:]) < 1, d["basin__SurfaceRunoff_mean"][:], 0) * gw).sum(1) * S
        qb = (np.where(np.abs(d["basin__AquiferBaseflow_mean"][:]) < 1, d["basin__AquiferBaseflow_mean"][:], 0) * gw).sum(1) * S
    df = pd.DataFrame({"P": p, "ET": -et, "Qsurf": qs, "Qbase": qb, "aquifer": aq}, index=t).iloc[1:]  # day 1's runoff is a fill
    wy = df.index.year + (df.index.month >= 10)
    out = df[["P", "ET", "Qsurf", "Qbase"]].groupby(wy).sum()
    out["aquifer_end"] = df["aquifer"].groupby(wy).last()
    return out.loc[: wy[-1] - 1].round(1)


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    scores = []
    for label in sys.argv[1:]:
        work = os.path.join(HERE, "slate_stream", "cheap_rerun", f"sample_87_{label}")
        s, clim = reach_scores("slate_stream", work)
        s["case"] = label
        scores.append(s)
        print(f"\n== {label}\nmonthly means at the gauge (Q m3/s, T C on observed days):\n{clim.round(2).T.to_string()}")
        print(f"water balance by water year (mm):\n{balance(work).to_string()}")
    print("\n" + pd.concat(scores).round(3).to_string(index=False))
