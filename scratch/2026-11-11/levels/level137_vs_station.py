#!/usr/bin/env python3
"""The raw forcing's air temperature (ERA5 model level 137) against each weather station by calendar month, on the
forcing's dry and wet hours: the station cell's temperature carried to the station's height at 6.5 K/km from the
cell elevation of forcing_ERA5.shp, and from ERA5's own orography. Prints the mean ERA5-minus-station difference (K).

    python scratch/2026-11-11/levels/level137_vs_station.py
"""
import glob
import os
import sys

import geopandas as gpd
import numpy as np
import xarray as xr
from netCDF4 import Dataset

HERE = os.path.dirname(os.path.abspath(__file__))
WF = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, WF)
import correct_forcing_to_station as cfs  # noqa: E402

STATIONS = {"Wolverine": ((60.39, -148.94), (990, 1420)), "Gulkana": ((63.27, -145.42), (1480, 1725))}
WET = 0.1  # mm/h


def raw_cell(dom, la, lo):
    """hours, temperature (K) and precipitation (mm/h) of the grid point nearest (la, lo)."""
    h, t, p = [], [], []
    for path in sorted(glob.glob(os.path.join(WF, "data", f"domain_{dom}", "forcing", "raw_data", "*_ERA5_merged_*.nc"))):
        with Dataset(path) as f:
            i, j = np.argmin(abs(f["latitude"][:] - la)), np.argmin(abs(f["longitude"][:] - lo))
            h.append(np.asarray(f["time"][:])); t.append(np.asarray(f["airtemp"][:, i, j])); p.append(np.asarray(f["pptrate"][:, i, j]) * 3600)
            cell = float(f["latitude"][i]), float(f["longitude"][j])
    return np.concatenate(h), np.concatenate(t), np.concatenate(p), cell


def main():
    oro = xr.open_dataset(os.path.join(HERE, "..", "lapse", "era5_sfc_monthly.nc"))["z"].isel(valid_time=0) / 9.80665
    for dom, ((la, lo), zs) in STATIONS.items():
        hours, t, pr, (cla, clo) = raw_cell(dom, la, lo)
        shp = gpd.read_file(os.path.join(WF, "data", f"domain_{dom}", "shapefiles", "forcing", "forcing_ERA5.shp"))
        z_shp = float(shp[(abs(shp.lat - cla) < 1e-4) & (abs(shp.lon - clo) < 1e-4)].elev_m.iloc[0])
        z_oro = float(oro.sel(latitude=cla, longitude=clo, method="nearest"))
        month = np.array([(cfs.EPOCH + cfs.timedelta(hours=int(h))).month for h in hours])
        print(f"{dom}: cell {cla}, {clo}; forcing_ERA5.shp {z_shp:.0f} m, ERA5 orography {z_oro:.0f} m")
        for z in zs:
            st = cfs.read_station(os.path.join(WF, "data", f"domain_{dom}", "observations", "stations", str(z)))["T"]
            obs = np.array([st.get(int(h), np.nan) for h in hours]) + 273.15
            for name, zc in (("shapefile", z_shp), ("orography", z_oro)):
                d = t - 0.0065 * (z - zc) - obs
                for kind, sel in (("dry", pr <= WET), ("wet", pr > WET)):
                    row = [np.nanmean(d[sel & (month == m)]) for m in range(1, 13)]
                    print(f"  {z} m {name} {kind} " + " ".join(f"{x:+5.1f}" for x in row))


if __name__ == "__main__":
    main()
