#!/usr/bin/env python3
"""Lapse rate by calendar month from ERA5 2 m temperature regressed on the cells' elevation, in windows of several
sizes around each basin, against the two stations' lapse (corrections.csv), WY2005-2024.

    python scratch/2026-11-11/lapse/surface_lapse.py
"""
import csv
import os

import numpy as np
import xarray as xr

HERE = os.path.dirname(os.path.abspath(__file__))
WF = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
BASINS = {"Wolverine": (60.39, -148.94), "Gulkana": (63.27, -145.42)}
HALF_WIDTHS = [(0.25, 0.5), (0.5, 1.0), (0.75, 1.5), (1.0, 2.0)]   # deg lat, lon


def station_lapse(dom):
    for r in csv.reader(open(os.path.join(WF, "data", f"domain_{dom}", "forcing", "SUMMA_input", "station_corrected",
                                          "corrections.csv"))):
        if r and r[0] == "lapse_rate_K_per_km":
            return np.array([float(x) for x in r[1:13]])


def main():
    ds = xr.open_dataset(os.path.join(HERE, "era5_sfc_monthly.nc"))
    t = "valid_time" if "valid_time" in ds.dims else "time"
    ds = ds.sel({t: slice("2004-10-01", "2024-09-30")})
    zs = (ds["z"].isel({t: 0}) / 9.80665)
    clim = ds["t2m"].groupby(f"{t}.month").mean()
    for dom, (la, lo) in BASINS.items():
        print(f"{dom}: stations " + " ".join(f"{x:5.1f}" for x in station_lapse(dom)))
        for dla, dlo in HALF_WIDTHS:
            sel = dict(latitude=slice(la + dla, la - dla), longitude=slice(lo - dlo, lo + dlo))
            z = zs.sel(sel).values.ravel()
            rates = [np.polyfit(z, clim.sel(month=m).sel(sel).values.ravel(), 1)[0] * 1000 for m in range(1, 13)]
            print(f"  +-{dla:.2f} x {dlo:.1f} deg, {z.size:3d} cells, {z.min():4.0f}-{z.max():4.0f} m: "
                  + " ".join(f"{x:5.1f}" for x in rates))


if __name__ == "__main__":
    main()
