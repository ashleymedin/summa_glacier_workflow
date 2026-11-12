#!/usr/bin/env python3
"""Winter ice on Wolverine's lake in the trial-459 infill run (lake_ice_run.sh): the ice cover, the ice in the water
layers below it, the liquid left, the inflow and outflow, by winter.

    ./lake_ice.py OUTPUT_DIR
"""
import glob
import sys

import netCDF4 as nc4
import numpy as np
import pandas as pd

H, D, NSOIL = 0, 3, 8  # the wetland: HRU 0, domain 3, eight soil layers below its water


def main():
    with nc4.Dataset(glob.glob(sys.argv[1] + "/*sample000001_day.nc")[0]) as d:
        t = pd.Timestamp("1990-01-01") + pd.to_timedelta(np.round(np.array(d["time"][:], float)), unit="s")
        dep = np.ma.filled(d["mLayerDepth"][:, :, H, D].astype(float), np.nan)
        ice = np.ma.filled(d["mLayerVolFracIce"][:, :, H, D].astype(float), np.nan)
        liq = np.ma.filled(d["mLayerVolFracLiq"][:, :, H, D].astype(float), np.nan)
        g = lambda v: np.ma.filled(d[v][:, H, D].astype(float), np.nan)
        x = pd.DataFrame({"cover": g("scalarLakeIceThick_mean"), "swe": g("scalarSWE_mean"), "area": g("DOMarea_mean"),
                          "qin": g("scalarStreamLatInflow_mean"), "qout": g("scalarStreamOutflow_mean")}, index=t)
    dep[dep < -1000] = np.nan
    ice[ice < -1000] = np.nan
    liq[liq < -1000] = np.nan
    nlay = np.sum(np.isfinite(dep), axis=1)
    top_ice, top_liq = np.zeros(len(t)), np.zeros(len(t))
    for i, n in enumerate(nlay):
        top_ice[i] = np.nansum(dep[i, :n - NSOIL] * ice[i, :n - NSOIL])
        top_liq[i] = np.nansum(dep[i, :n - NSOIL] * liq[i, :n - NSOIL])
    x["ice"] = top_ice - x.swe / 917.0  # ice in the water layers (m of ice), the snow taken out
    x["liq"] = top_liq
    x = x[x.area > 0]
    w = x[x.index.month.isin([11, 12, 1, 2, 3, 4])]
    win = w.groupby(np.where(w.index.month >= 11, w.index.year + 1, w.index.year))
    print("winter  max cover  max water-layer ice  min liquid  mean inflow  mean outflow (m3/s)  max SWE  area")
    for y, v in win:
        print(f"{y}  {v.cover.max():8.2f}  {v.ice.max():8.2f}  {v.liq.min():8.3f}  {v.qin.mean():8.3f}  {v.qout.mean():8.3f}"
              f"  {v.swe.max():6.0f}  {v.area.median():7.0f}")
    y = x["2021-10-01":"2022-06-30"].resample("MS").mean()
    print(y[["cover", "ice", "liq", "qin", "qout", "swe", "area"]].round(3).to_string())


if __name__ == "__main__":
    main()
