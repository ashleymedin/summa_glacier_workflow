#!/usr/bin/env python3
"""The free-air temperature and relative humidity of the ERA5 pressure levels (forcing/raw_levels) at each weather
station's height against the station, hour by hour, on the forcing's dry and wet hours of each calendar month, beside
the raw forcing's near-surface temperature (model level 137) carried there at 6.5 K/km from ERA5's surface.

The free air is read as remap_forcing.py reads it, from the levels CLEAR m and more over ERA5's surface, for several
CLEAR; "from +300 m" uses only the levels 300 m and more over the station, the case of an HRU under ERA5's surface.
Prints the mean ERA5-minus-station difference (K, and % relative humidity) and the hourly RMS difference.

    python scratch/2026-11-11/levels/levels_vs_station.py
"""
import glob
import os
import sys

import numpy as np
from netCDF4 import Dataset

HERE = os.path.dirname(os.path.abspath(__file__))
WF = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, WF)
import correct_forcing_to_station as cfs  # noqa: E402
import remap_forcing as rf  # noqa: E402

STATIONS = {"Wolverine": ((60.39, -148.94), (990, 1420)), "Gulkana": ((63.27, -145.42), (1480, 1725))}
WET = 0.1  # mm/h
CLEARS = (0.0, 100.0, 200.0)


def main():
    for dom, ((la, lo), zs) in STATIONS.items():
        base = os.path.join(WF, "data", f"domain_{dom}", "forcing")
        hours, t137, q137, sp, pr, cols = [], [], [], [], [], {}
        paths = sorted(glob.glob(os.path.join(base, "raw_levels", "*_ERA5_levels_*.nc")))
        for lev_path, after in zip(paths, paths[1:] + [None]):
            with Dataset(lev_path.replace("raw_levels", "raw_data").replace("_levels_", "_merged_")) as f:
                i, j = np.argmin(abs(f["latitude"][:] - la)), np.argmin(abs(f["longitude"][:] - lo))
                f_lat, f_lon = f["latitude"][:], f["longitude"][:]
                cla, clo = float(f_lat[i]), float(f_lon[j])
                h = np.asarray(f["time"][:])
                hours.append(h); t137.append(np.asarray(f["airtemp"][:, i, j], "f8")); pr.append(np.asarray(f["pptrate"][:, i, j]) * 3600)
                q137.append(np.asarray(f["spechum"][:, i, j], "f8")); sp.append(np.asarray(f["airpres"][:, i, j], "f8"))
            lev = rf.read_levels(lev_path, after, np.asarray(h, dtype="f8"))
            z0 = rf.cell_elevation(os.path.join(base, "raw_levels", f"domain_{dom}_ERA5_orography.nc"), f_lat, f_lon)[i, j]
            for z in zs:
                for name, floor in [(f"free air, clear {c:.0f} m", z0 + c) for c in CLEARS] + [("free air from +300 m", z + 300.0)]:
                    at = rf.column(lev["h"][:, :, i, j], z, floor)
                    cols.setdefault((z, name), []).append((at(lev["t"][:, :, i, j]), np.clip(at(lev["rh"][:, :, i, j]), 0.01, 1.0)))
        if not hours:
            print(f"{dom}: no levels yet")
            continue
        hours, t137, q137, sp, pr = (np.concatenate(x) for x in (hours, t137, q137, sp, pr))
        month = np.array([(cfs.EPOCH + cfs.timedelta(hours=int(h))).month for h in hours])
        rh137 = np.minimum(1.0, rf.relhum(q137, sp, t137))
        print(f"{dom}: cell {cla}, {clo}, ERA5 surface {z0:.0f} m, {len(hours) // 24} days")
        for z in zs:
            st = cfs.read_station(os.path.join(WF, "data", f"domain_{dom}", "observations", "stations", str(z)))
            obs_t = np.array([st["T"].get(int(h), np.nan) for h in hours]) + 273.15
            obs_rh = np.array([st.get("RH", {}).get(int(h), np.nan) for h in hours]) / 100.0
            rows = [("level 137 at 6.5 K/km", t137 - 0.0065 * (z - z0), rh137)]
            rows += [(name, np.concatenate([c[0] for c in v]), np.concatenate([c[1] for c in v])) for (zz, name), v in cols.items() if zz == z]
            print(f"  {z} m, hours with station T {np.isfinite(obs_t).sum()}, RH {np.isfinite(obs_rh).sum()}")
            for name, t, rh in rows:
                for kind, sel in (("dry", pr <= WET), ("wet", pr > WET)):
                    d = t - obs_t
                    bias = " ".join(f"{np.nanmean(d[sel & (month == m)]):+5.1f}" if np.isfinite(d[sel & (month == m)]).sum() > 48 else "    ." for m in range(1, 13))
                    ok = sel & np.isfinite(d)
                    print(f"    T  {name:24s} {kind} {bias}   rms {np.sqrt(np.mean(d[ok] ** 2)):4.2f}")
                d = 100 * (rh - obs_rh)
                if np.isfinite(d).sum() > 48:
                    bias = " ".join(f"{np.nanmean(d[month == m]):+5.0f}" if np.isfinite(d[month == m]).sum() > 48 else "    ." for m in range(1, 13))
                    print(f"    RH {name:24s} all {bias}   rms {np.sqrt(np.nanmean(d ** 2)):4.1f}")


if __name__ == "__main__":
    main()
