#!/usr/bin/env python3
"""Remap a domain's gridded ERA5 (forcing/raw_data) to its HRUs as SUMMA forcing (forcing/SUMMA_input).

Each HRU takes the mean of the ERA5 cells it overlaps, weighted by the overlap area: the 0.25-degree cell
of each grid point is intersected with the HRU polygons of shapefiles/catchment/<domain>_HRUs_elevation.shp
in an equal-area projection.  The variables are then carried from the same weighting of the cells' elevations
(elev_m of shapefiles/forcing/forcing_ERA5.shp) to the HRU's elev_mean: air temperature by the month's lapse rate,
pressure hypsometrically at the mean of the two temperatures, specific humidity at the cells' relative humidity, and
longwave at the cells' sky emissivity (by the fourth power of the temperature ratio).  With precip_climatology
in the YAML (acquire_climatology.py), precipitation is scaled by the HRU's mean climatology over the same weighting
of the cells' mean, the climatology's pattern within the ERA5 cells.  Every month of raw_data is written, one file per month, with the names
the rest of the pipeline reads.  Variables, units and time (hours since 1900-01-01 UTC) pass through.

    ./remap_forcing.py domains/gulkana.yaml
"""

import argparse
import glob
import os

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from netCDF4 import Dataset, num2date
from shapely.geometry import box

from domain_config import load_config

VARS = ("airpres", "LWRadAtm", "SWRadAtm", "pptrate", "airtemp", "spechum", "windspd")
HALF = 0.125                       # deg, half an ERA5 cell
LAPSE = 0.0065                     # K m-1, temperature decrease with height
G, R_DRY = 9.80665, 287.05         # m s-2, J kg-1 K-1
TFREEZE, SATVPFRZ, W_RATIO = 273.16, 610.8, 0.622   # SUMMA's convert_funcs constants
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


def raster_mean(a, transform, geom):
    """Mean of the raster cells whose centres the polygon holds, or that it touches when it holds none."""
    m = ~geometry_mask([geom], a.shape, transform)
    if not m.any():
        m = ~geometry_mask([geom], a.shape, transform, all_touched=True)
    return np.nanmean(a[m])


def precip_ratio(path, hrus, lat, lon, w):
    """Each HRU's mean of the climatology raster over the overlap-weighted mean of its ERA5 cells'."""
    with rasterio.open(path) as r:
        a = r.read(1, masked=True).astype("f8").filled(np.nan)
        transform = r.transform
    cell = np.zeros((len(lat), len(lon)))
    for i, j in zip(*np.nonzero(w.sum(axis=0))):
        cell[i, j] = raster_mean(a, transform, box(lon[j] - HALF, lat[i] - HALF, lon[j] + HALF, lat[i] + HALF))
    hru = np.array([raster_mean(a, transform, g) for g in hrus.to_crs(4326).geometry])
    return hru / np.sum(w * cell, axis=(1, 2))


def relhum(q, p, t):
    """Relative humidity (-) from specific humidity, pressure (Pa) and temperature (K), as SUMMA's SPHM2RELHM."""
    e_sat = SATVPFRZ * np.exp(17.27 * (t - TFREEZE) / (237.30 + t - TFREEZE))
    return q * p / (e_sat * (W_RATIO + q * (1.0 - W_RATIO)))


def spechum(rh, p, t):
    """Specific humidity (kg kg-1) from relative humidity, pressure (Pa) and temperature (K), as SUMMA's RELHM2SPHM."""
    e = rh * SATVPFRZ * np.exp(17.27 * (t - TFREEZE) / (237.30 + t - TFREEZE))
    return e * W_RATIO / (p - (1.0 - W_RATIO) * e)


def to_hru(f, dz, lapse):
    """The cell-weighted forcing (time, hru) carried up dz (m, HRU less cells) at lapse (time,) K m-1."""
    t = f["airtemp"] - lapse[:, None] * dz[None, :]
    p = f["airpres"] * np.exp(-G * dz[None, :] / (R_DRY * 0.5 * (f["airtemp"] + t)))
    rh = np.minimum(1.0, relhum(f["spechum"], f["airpres"], f["airtemp"]))
    return {**f, "airtemp": t, "airpres": p, "spechum": spechum(rh, p, t),
            "LWRadAtm": f["LWRadAtm"] * (t / f["airtemp"]) ** 4}


def remap(path, out, w, dz, lapse, hrus, ratio):
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
        month = np.array([d.month for d in num2date(src["time"][:], src["time"].units)])
        f = {name: np.einsum("tij,kij->tk", np.asarray(src[name][:], dtype="f8"), w) for name in VARS}
        f = to_hru(f, dz, lapse[month])
        f["pptrate"] = f["pptrate"] * ratio[None, :]
        for name in VARS:
            s = src[name]
            v = dst.createVariable(name, "f8" if name == "airtemp" else "f4", ("time", "hru"), fill_value=FILL)
            v.setncatts({k: s.getncattr(k) for k in ("long_name", "units") if k in s.ncattrs()})
            v[:] = f[name]
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
    dz = hrus.elev_mean.values - np.nansum(w * z, axis=(1, 2))
    lapse = np.full(13, LAPSE)  # by calendar month, index 0 unused
    ratio = precip_ratio(c["precip_climatology"], hrus, lat, lon, w) if "precip_climatology" in c else np.ones(len(hrus))
    print("precipitation ratio by HRU:", np.round(ratio, 3))
    out_dir = os.path.join(project, "forcing", "SUMMA_input")
    os.makedirs(out_dir, exist_ok=True)
    for path in raw:
        remap(path, os.path.join(out_dir, f"{dom}_ERA5_remapped_{os.path.basename(path)}"), w, dz, lapse, hrus, ratio)
    with open(os.path.join(out_dir, "remap.csv"), "w") as f:
        f.write("lapse_rate_K_per_km," + ",".join(f"{-1000 * lapse[m]:.2f}" for m in range(1, 13)) + "\n")
        f.write("precip_ratio," + ",".join(f"{r:.4f}" for r in ratio) + "\n")
    print(f"{len(raw)} months remapped to {out_dir}")


if __name__ == "__main__":
    main()
