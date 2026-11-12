#!/usr/bin/env python3
"""Fit wetlandSedConc offline: the sediment the Wolverine lake traps does not change the glacier runoff it takes, so
the trial-459 lake run's daily inflow and basin area give the infilled full area for any concentration, as SUMMA
computes it (wetlandInfillShape 1). Fitted to the imagery's Jul-Sep median area by year since 2020.

    ./infill_fit.py RUNS_DIR LAKE_DIR      runs/wolverine_stream/calibration_added_rerun  data/domain_Wolverine/observations/lake_area
"""
import glob
import os
import sys

import netCDF4 as nc4
import numpy as np
import pandas as pd

DEPTH, SHAPE_A = 2.25, 1.0


def imagery(lake_dir):
    x = pd.concat([pd.read_csv(os.path.join(lake_dir, f), parse_dates=["date"])
                   for f in ("wolverine_lake_landsat.csv", "wolverine_lake_sentinel2.csv")])
    x = x[(x.bad < 0.05) & (x.snow < 0.05) & x.date.dt.month.isin([7, 8, 9])]
    x = x.groupby("date").water_km2.median()
    return x.groupby(x.index.year).median()


def main():
    runs_dir, lake_dir = sys.argv[1:3]
    out = glob.glob(os.path.join(runs_dir, "sample_459_lake", "output", "*sample000001_day.nc"))[0]
    with nc4.Dataset(out) as d:
        t = pd.Timestamp("1990-01-01") + pd.to_timedelta(np.round(np.array(d["time"][:], float)), unit="s")
        g = lambda v: np.ma.filled(d[v][:, 0, 3].astype(float), np.nan)
        x = pd.DataFrame({"qin": g("scalarStreamLatInflow_mean"), "basin": g("scalarWetlandFullArea_mean"),
                          "area": g("DOMarea_mean")}, index=t).fillna(0)
    img = imagery(lake_dir)
    print("glacier runoff into the open lake (1e6 m3/yr):",
          (x.qin.where(x.area > 0, 0).groupby(x.index.year).sum() * 86400 / 1e6).round(1).to_dict())
    best = None
    rows = {}
    for c in np.geomspace(1e-5, 1e-3, 41):
        sed, full = 0.0, []
        for q, a, op in zip(x.qin, x.basin, x.area):
            if op > 0 and a > 0:
                sed = min(sed + c * q * 86400, a * DEPTH)
            f = sed / (a * DEPTH) if a > 0 else 0
            full.append(a * (1 - f) ** SHAPE_A)
        s = pd.Series(full, index=x.index) / 1e6
        jas = s[s.index.month.isin([7, 8, 9])]
        yr = jas.groupby(jas.index.year).median()
        e = (yr.reindex(img.index) - img)[lambda v: v.index >= 2020].dropna()
        rmse = np.sqrt((e ** 2).mean())
        rows[c] = (rmse, yr)
        if best is None or rmse < best[1]:
            best = (c, rmse)
    c, rmse = best
    print(f"best wetlandSedConc {c:.2e} (RMSE {rmse * 1e3:.1f} x1e-3 km2 over 2020-2026)")
    for cc in sorted(rows, key=lambda k: abs(np.log(k / c)))[:1] + [k for k in rows if abs(np.log(k / c)) > 0.6][:0]:
        pass
    yr = rows[c][1]
    print("year  model  imagery")
    for y in range(2006, 2027):
        print(y, f"{yr.get(y, np.nan):.4f}", f"{img.get(y, np.nan):.4f}")
    for k in (c / 2, c * 2):
        kk = min(rows, key=lambda z: abs(np.log(z / k)))
        print(f"  at {kk:.1e}: RMSE {rows[kk][0] * 1e3:.1f}x1e-3 km2, 2020 {rows[kk][1].get(2020):.4f} 2026 {rows[kk][1].get(2026):.4f}")


if __name__ == "__main__":
    main()
