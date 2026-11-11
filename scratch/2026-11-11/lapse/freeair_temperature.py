#!/usr/bin/env python3
"""ERA5 against each weather station by calendar month, over the year-months the station nearly fills, WY2005-2024:
the station cell's 2 m temperature carried to the station's height at 6.5 K/km, and the free-air temperature of the
pressure levels at the station's height. Prints the mean ERA5-minus-station difference (K) of each.

    python scratch/2026-11-11/lapse/freeair_temperature.py
"""
import os
import sys
from datetime import timedelta

import numpy as np
import xarray as xr

from surface_lapse import BASINS, HERE, WF

sys.path.insert(0, WF)
import correct_forcing_to_station as cfs  # noqa: E402

STATIONS = {"Wolverine": (990, 1420), "Gulkana": (1480, 1725)}


def station_months(dom, z):
    """{(year, month): mean degC} of the year-months with over 90% of their hours."""
    t = cfs.read_station(os.path.join(WF, "data", f"domain_{dom}", "observations", "stations", str(z)))["T"]
    acc = {}
    for h, v in t.items():
        if np.isfinite(v):
            d = cfs.EPOCH + timedelta(hours=int(h))
            s = acc.setdefault((d.year, d.month), [0.0, 0])
            s[0] += v; s[1] += 1
    return {k: s[0] / s[1] for k, s in acc.items() if s[1] > 0.9 * 24 * 28}


def main():
    sfc = xr.open_dataset(os.path.join(HERE, "era5_sfc_monthly.nc"))
    pl = xr.open_dataset(os.path.join(HERE, "era5_pl_monthly.nc"))
    t = "valid_time" if "valid_time" in sfc.dims else "time"
    for dom, (la, lo) in BASINS.items():
        s, p = sfc.sel(latitude=la, longitude=lo, method="nearest"), pl.sel(latitude=la, longitude=lo, method="nearest")
        zs = float(s["z"].isel({t: 0})) / 9.80665
        print(f"{dom}: ERA5 cell at {zs:.0f} m")
        for z in STATIONS[dom]:
            d2m, dfa, n = np.zeros(13), np.zeros(13), np.zeros(13)
            for (y, m), obs in station_months(dom, z).items():
                when = f"{y}-{m:02d}"
                if not ("2004-10" <= when <= "2024-09"):
                    continue
                c = p.sel({t: when}).squeeze()
                h, tk = (c["z"] / 9.80665).values, c["t"].values
                o = np.argsort(h)
                d2m[m] += float(s["t2m"].sel({t: when}).squeeze()) - 0.0065 * (z - zs) - 273.15 - obs
                dfa[m] += np.interp(z, h[o], tk[o]) - 273.15 - obs
                n[m] += 1
            print(f"  {z} m, months used " + " ".join(f"{int(x):5d}" for x in n[1:]))
            print("    2 m at 6.5 K/km " + " ".join(f"{x:+5.1f}" for x in d2m[1:] / n[1:]))
            print("    free air        " + " ".join(f"{x:+5.1f}" for x in dfa[1:] / n[1:]))


if __name__ == "__main__":
    main()
