#!/usr/bin/env python3
"""Lapse rate by calendar month from ERA5's free-air temperature profile over each basin's cell (pressure levels,
monthly means), between the two stations' heights and across the HRUs' span, against the stations' lapse, WY2005-2024.

    python scratch/2026-11-11/lapse/freeair_lapse.py
"""
import os

import numpy as np
import xarray as xr

from surface_lapse import BASINS, HERE, station_lapse

SPANS = {"Wolverine": [(990, 1420), (738, 1413)], "Gulkana": [(1480, 1725), (1331, 2046)]}


def main():
    ds = xr.open_dataset(os.path.join(HERE, "era5_pl_monthly.nc"))
    t = "valid_time" if "valid_time" in ds.dims else "time"
    lev = "pressure_level" if "pressure_level" in ds.dims else "level"
    ds = ds.sel({t: slice("2004-10-01", "2024-09-30")})
    for dom, (la, lo) in BASINS.items():
        col = ds.sel(latitude=la, longitude=lo, method="nearest")
        print(f"{dom}: stations " + " ".join(f"{x:5.1f}" for x in station_lapse(dom)))
        for z0, z1 in SPANS[dom]:
            rates = []
            for m in range(1, 13):
                c = col.sel({t: col[t].dt.month == m}).mean(t)
                h, tk = (c["z"] / 9.80665).values, c["t"].values
                o = np.argsort(h)
                rates.append((np.interp(z1, h[o], tk[o]) - np.interp(z0, h[o], tk[o])) / (z1 - z0) * 1000)
            print(f"  free air {z0}-{z1} m: " + " ".join(f"{x:5.1f}" for x in rates))


if __name__ == "__main__":
    main()
