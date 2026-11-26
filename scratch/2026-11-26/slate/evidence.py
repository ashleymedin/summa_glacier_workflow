#!/usr/bin/env python3
"""What Slate Creek's gauge says about where its late-summer water comes from: winter flow, recession rates after the melt,
and rain-event response, gauged against cheap trial 87 (bedrockLyrs rerun) and the basin's daily precipitation."""
import os
import sys

import netCDF4 as nc4
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slate_default import HERE, WF, obs_series  # noqa: E402

OBS = os.path.join(WF, "data/domain_SlateCreek/observations/calibration")
qo = obs_series(os.path.join(OBS, "USGS_15564879_daily_flow.nc"), "q_obs")
print(f"gauge record {qo.index[0].date()}..{qo.index[-1].date()}, {qo.notna().sum()} days")
m = qo.groupby(qo.index.month)
print("monthly: days with data, mean, median, share of exact zeros")
print(pd.DataFrame({"n": m.count(), "mean": m.mean().round(3), "median": m.median().round(3),
                    "zero": m.apply(lambda x: (x == 0).mean()).round(2)}).T.to_string())

# recession: daily log decline on dry days, July 15 - October 15
def recession(q):
    k = -np.log(q / q.shift(1))
    ok = (q.index.month.isin([7, 8, 9, 10])) & (q.diff() < 0) & (q.shift(1) > 0.05)
    return k[ok]

k = recession(qo).dropna()
print("\nobserved recession, falling days Jul-Oct: median k (1/day) by month",
      k.groupby(k.index.month).median().round(3).to_dict(), "-> e-folding days",
      (1 / k.groupby(k.index.month).median()).round(1).to_dict())
lowest = qo[qo.index.month.isin([8, 9])].groupby(qo[qo.index.month.isin([8, 9])].index.year).min()
print("yearly Aug-Sep minimum flow (m3/s):", lowest.round(2).to_dict())

work = os.path.join(HERE, "slate_stream", "cheap_rerun", "sample_87_bedrock", "output")
f = [x for x in os.listdir(work) if x.endswith("_timestep.nc") and "spinup" not in x][0]
with nc4.Dataset(os.path.join(work, f)) as d:
    t = pd.to_datetime(nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)) - pd.Timedelta(hours=9)
    qs = pd.Series(np.ma.filled(d["Q_reach"][:, 2, 0], np.nan), index=t).resample("D").mean()
f = [x for x in os.listdir(work) if x.endswith("_day.nc") and "spinup" not in x][0]
with nc4.Dataset(os.path.join(work, f)) as d:
    d.set_auto_mask(False)
    t = pd.to_datetime(nc4.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False))
    a = d["DOMarea_mean"][0, :, 0]
    w = np.where(a > 0, a, 0) / np.where(a > 0, a, 0).sum()
    rain = pd.Series((d["scalarRainfall_mean"][:, :, 0] * w).sum(1) * 86400, index=t)
    et = pd.Series(-(d["scalarTotalET_mean"][:, :, 0] * w).sum(1) * 86400, index=t)
ks = recession(qs).dropna()
print("simulated recession median k by month", ks.groupby(ks.index.month).median().round(3).to_dict())

# rain events: Jul-Sep days with > 10 mm basin rain, flow rise over the next 3 days
obs = qo.reindex(qs.index)
ev = rain[(rain > 10) & rain.index.month.isin([7, 8, 9])].index.normalize()
rows = []
for day in ev:
    if day - pd.Timedelta(days=1) not in obs.index or day + pd.Timedelta(days=3) not in obs.index:
        continue
    b0, s0 = obs[day - pd.Timedelta(days=1)], qs[day - pd.Timedelta(days=1)]
    rows.append(dict(day=day.date(), rain_mm=round(rain[day], 1), obs_before=round(b0, 2),
                     obs_peak=round(obs[day:day + pd.Timedelta(days=3)].max(), 2),
                     sim_before=round(s0, 2), sim_peak=round(qs[day:day + pd.Timedelta(days=3)].max(), 2)))
print("\nJul-Sep rain days over 10 mm, flow the day before and the peak within 3 days (m3/s):")
print(pd.DataFrame(rows).to_string(index=False))
jja = lambda s: s[s.index.month.isin([6, 7, 8, 9])]
wy = lambda s: s.groupby(s.index.year).sum()
print("\nJun-Sep basin rain and ET by year (mm):", pd.DataFrame({"rain": wy(jja(rain)), "ET": wy(jja(et))}).round(0).T.to_string())
