#!/usr/bin/env python3
"""Remap a domain's gridded ERA5 (forcing/raw_data) to its HRUs as SUMMA forcing (forcing/SUMMA_input).

Each HRU takes the mean of the ERA5 cells it overlaps, weighted by the overlap area: the 0.25-degree cell
of each grid point is intersected with the HRU polygons of shapefiles/catchment/<domain>_HRUs_elevation.shp
in an equal-area projection.  Air temperature is then lapsed at 6.5 K km-1 from the same weighting of the
cells' elevations (elev_m of shapefiles/forcing/forcing_ERA5.shp) to the HRU's elev_mean.  Every month of raw_data is written, one file per month, with the names
the rest of the pipeline reads.  Variables, units and time (hours since 1900-01-01 UTC) pass through.

    ./remap_forcing.py domains/gulkana.yaml
"""

import argparse
import glob
import os

import geopandas as gpd
import numpy as np
from netCDF4 import Dataset
from shapely.geometry import box

from domain_config import load_config

VARS = ("airpres", "LWRadAtm", "SWRadAtm", "pptrate", "airtemp", "spechum", "windspd")
HALF = 0.125                       # deg, half an ERA5 cell
LAPSE = 0.0065                     # K m-1
FILL = -9999.0


def weights(hrus, lat, lon):
    """(hru, lat, lon) overlap-area fractions of each HRU over the grid cells."""
    cells = gpd.GeoDataFrame({"i": [i for i in range(len(lat)) for _ in lon], "j": [j for _ in lat for j in range(len(lon))]},
                             geometry=[box(x - HALF, y - HALF, x + HALF, y + HALF) for y in lat for x in lon], crs="EPSG:4326")
    ea = f"+proj=laea +lat_0={hrus.center_lat.mean()} +lon_0={hrus.center_lon.mean()}"
    w = np.zeros((len(hrus), len(lat), len(lon)))
    for k, poly in enumerate(hrus.to_crs(ea).geometry):
        for i, j, cell in zip(cells.i, cells.j, cells.to_crs(ea).geometry):
            w[k, i, j] = poly.intersection(cell).area
        if w[k].sum() < 0.999 * poly.area:
            raise SystemExit(f"HRU {hrus.HRU_ID.iloc[k]} reaches beyond the raw ERA5 grid")
        w[k] /= w[k].sum()
    return w


def cell_elevation(shapefile, lat, lon):
    """(lat, lon) ERA5 cell elevation, m; NaN for a cell the shapefile leaves out."""
    z = np.full((len(lat), len(lon)), np.nan)
    for _, r in gpd.read_file(shapefile).iterrows():
        i, j = np.argmin(abs(lat - r.lat)), np.argmin(abs(lon - r.lon))
        if abs(lat[i] - r.lat) < 1e-4 and abs(lon[j] - r.lon) < 1e-4:
            z[i, j] = r.elev_m
    return z


def remap(path, out, w, dT, hrus):
    with Dataset(path) as src, Dataset(out, "w") as dst:
        dst.createDimension("time", None)
        dst.createDimension("hru", len(hrus))
        t = dst.createVariable("time", "i4", ("time",))
        t.setncatts({"long_name": "time", "standard_name": "time", "axis": "T",
                     "units": "hours since 1900-01-01", "calendar": "gregorian"})
        t[:] = src["time"][:]
        for name, attr, units in (("latitude", "center_lat", "degrees_north"), ("longitude", "center_lon", "degrees_east")):
            v = dst.createVariable(name, "f8", ("hru",))
            v.setncatts({"long_name": name, "units": units, "standard_name": name})
            v[:] = hrus[attr].values
        v = dst.createVariable("hruId", "f8", ("hru",))
        v.setncatts({"long_name": "shape ID", "units": "1"})
        v[:] = hrus.HRU_ID.values
        for name in VARS:
            s = src[name]
            v = dst.createVariable(name, "f8" if name == "airtemp" else "f4", ("time", "hru"), fill_value=FILL)
            v.setncatts({k: s.getncattr(k) for k in ("long_name", "units") if k in s.ncattrs()})
            v[:] = np.einsum("tij,kij->tk", np.asarray(s[:], dtype="f8"), w) + (dT if name == "airtemp" else 0.0)
        v = dst.createVariable("data_step", "i8")
        v.setncatts({"long_name": "data step length in seconds", "units": "s"})
        v.assignValue(3600)
        dst.setncatts({"Conventions": "CF-1.6", "Source": f"remap_forcing.py, area-weighted from {os.path.basename(path)}"})


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    a = p.parse_args()
    c = load_config(a.config)
    dom, project = c["domain"], c["project_dir"]
    raw = sorted(glob.glob(os.path.join(project, "forcing", "raw_data", f"domain_{dom}_ERA5_merged_*.nc")))
    if not raw:
        raise SystemExit("no raw ERA5 in forcing/raw_data; run acquire_era5.py first")
    hrus = gpd.read_file(os.path.join(project, "shapefiles", "catchment", f"{dom}_HRUs_elevation.shp")).sort_values("HRU_ID")
    with Dataset(raw[0]) as f:
        lat, lon = f["latitude"][:], f["longitude"][:]
    w = weights(hrus, lat, lon)
    z = cell_elevation(os.path.join(project, "shapefiles", "forcing", "forcing_ERA5.shp"), lat, lon)
    if np.isnan(z[w.sum(axis=0) > 0]).any():
        raise SystemExit("forcing_ERA5.shp has no elevation for a cell an HRU overlaps")
    dT = LAPSE * (np.nansum(w * z, axis=(1, 2)) - hrus.elev_mean.values)
    out_dir = os.path.join(project, "forcing", "SUMMA_input")
    os.makedirs(out_dir, exist_ok=True)
    for path in raw:
        remap(path, os.path.join(out_dir, f"{dom}_ERA5_remapped_{os.path.basename(path)}"), w, dT, hrus)
    print(f"{len(raw)} months remapped to {out_dir}")


if __name__ == "__main__":
    main()
