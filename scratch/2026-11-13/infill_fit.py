#!/usr/bin/env python3
"""Fit wetlandSedConc and wetlandSettleVel offline. The sediment Wolverine's lake traps does not change the glacier
runoff it takes, so the trial-459 lake run's daily inflow and ice-free basin give the infilled full area for any pair,
as SUMMA computes it (wetlandInfillShape 1; the share that settles 1 - exp(-w_s A / Q)). Fitted to the imagery's
July-August median area by year from 2013: clear scenes (bad < 0.05) with under half the box snow or ice, since the
glacier tongue sits in the box until about 2016; earlier and late-season scenes are glacier, snow or low-sun shadow.
Also prints the area with no sediment, the most the ice-free basin allows.

    ./infill_fit.py RUNS_DIR LAKE_DIR      runs/wolverine_stream/calibration_added_rerun  data/domain_Wolverine/observations/lake_area
"""
import glob
import os
import sys

import netCDF4 as nc4
import numpy as np
import pandas as pd

DEPTH = 2.25
MONTHS = [7, 8]


def imagery(lake_dir):
    x = pd.concat([pd.read_csv(os.path.join(lake_dir, f), parse_dates=["date"])
                   for f in ("wolverine_lake_landsat.csv", "wolverine_lake_sentinel2.csv")])
    x = x[(x.bad < 0.05) & (x.snow < 0.5) & x.date.dt.month.isin(MONTHS) & (x.date.dt.year >= 2013)]
    x = x.groupby("date").water_km2.median()
    return x.groupby(x.index.year).median()


def infill(basin, qin, conc, settle):
    sed, full = 0.0, np.zeros(len(basin))
    for i, (b, q) in enumerate(zip(basin, qin)):
        if b > 0:
            if q > 0:
                trap = 1 - np.exp(-settle * (b - sed / DEPTH) / q)
                sed = min(sed + conc * trap * q * 86400, b * DEPTH)
            full[i] = b - sed / DEPTH
    return full


def main():
    runs_dir, lake_dir = sys.argv[1:3]
    out = glob.glob(os.path.join(runs_dir, "sample_459_lake", "output", "*sample000001_day.nc"))[0]
    with nc4.Dataset(out) as d:
        t = pd.Timestamp("1990-01-01") + pd.to_timedelta(np.round(np.array(d["time"][:], float)), unit="s")
        g = lambda v: np.ma.filled(d[v][:, 0, 3].astype(float), np.nan)
        x = pd.DataFrame({"basin": g("scalarWetlandFullArea_mean"), "qin": g("scalarStreamLatInflow_mean")}, index=t).fillna(0)
    img = imagery(lake_dir)

    def yearly(full):
        s = pd.Series(full, index=x.index) / 1e6
        s = s[s.index.month.isin(MONTHS)]
        return s.groupby(s.index.year).median()

    def rmse(yr):
        e = (yr.reindex(img.index) - img).dropna()
        return np.sqrt((e ** 2).mean())

    print("year   imagery  no sediment")
    free = yearly(x.basin.values)
    for y in range(2013, 2027):
        print(y, f"{img.get(y, np.nan):.4f}", f"{free.get(y, np.nan):.4f}")
    for settle in (1e-6, 3e-6, 1e-5, 3e-5, 1e-4, 1e-3, 1.0):
        fits = [(rmse(yearly(infill(x.basin.values, x.qin.values, c, settle))), c) for c in np.geomspace(3e-5, 3e-2, 31)]
        err, c = min(fits)
        print(f"wetlandSettleVel {settle:.0e} m/s: wetlandSedConc {c:.1e} (about {c * 1600:.2f} kg/m3 at 1.6 t/m3), "
              f"RMSE {err * 1e3:.1f}e-3 km2")


if __name__ == "__main__":
    main()
