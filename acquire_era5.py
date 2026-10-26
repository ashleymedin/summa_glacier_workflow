#!/usr/bin/env python3
"""Fetch a domain's hourly ERA5 from the Copernicus Climate Data Store into forcing/raw_data, one file a month.

The fields are those of the domain's 2008-2022 record, as the CWARHM ERA5 pull made them: temperature,
specific humidity and wind at the lowest model level (137, about 10 m) from reanalysis-era5-complete, and
surface pressure and the mean downward shortwave, longwave and total precipitation rates from
reanalysis-era5-single-levels, on the 0.25-degree grid.  Each month is written as
domain_<domain>_ERA5_merged_YYYYMM.nc with airtemp (K), spechum (kg kg-1), windspd (m s-1), airpres (Pa),
SWRadAtm and LWRadAtm (W m-2) and pptrate (kg m-2 s-1), time in hours since 1900-01-01 UTC at the end of
each hour, which remap_forcing.py then takes to the HRUs.  Months already in raw_data are skipped.

The grid is that of the files already in raw_data, else the cells the HRUs overlap and one more around.
Downloading needs a free CDS account, the ERA5 licence accepted on the dataset pages, and its key in ~/.cdsapirc
(url: https://cds.climate.copernicus.eu/api, key: <key>).  The model-level requests come off tape and take hours.

    ./acquire_era5.py domains/gulkana.yaml 2004-10 2026-09
"""

import argparse
import glob
import os
import tempfile
from datetime import datetime, timezone

import geopandas as gpd
import numpy as np
import xarray as xr

from domain_config import load_config

STEP = 0.25                                  # deg, ERA5 grid
EPOCH = datetime(1900, 1, 1)
SURFACE = {"sp": "airpres", "avg_sdswrf": "SWRadAtm", "avg_sdlwrf": "LWRadAtm", "avg_tprate": "pptrate",
           "msdwswrf": "SWRadAtm", "msdwlwrf": "LWRadAtm", "mtpr": "pptrate"}  # new and old CDS short names
ATTRS = {"airtemp": ("Temperature", "K"), "spechum": ("Specific humidity", "kg kg**-1"),
         "windspd": ("wind speed at the measurement height, computed from ERA5 U and V-components", "m s**-1"),
         "airpres": ("Surface pressure", "Pa"), "SWRadAtm": ("Mean surface downward short-wave radiation flux", "W m**-2"),
         "LWRadAtm": ("Mean surface downward long-wave radiation flux", "W m**-2"),
         "pptrate": ("Mean total precipitation rate", "kg m**-2 s**-1")}


def grid_area(project, dom, raw_dir):
    """[north, west, south, east] of the grid points, deg."""
    old = sorted(glob.glob(os.path.join(raw_dir, f"domain_{dom}_ERA5_merged_*.nc")))
    if old:
        with xr.open_dataset(old[0]) as f:
            return [float(f.latitude.max()), float(f.longitude.min()), float(f.latitude.min()), float(f.longitude.max())]
    w, s, e, n = gpd.read_file(os.path.join(project, "shapefiles", "catchment", f"{dom}_HRUs_elevation.shp")).total_bounds
    snap = lambda x, f: f(x / STEP) * STEP
    return [float(x) for x in (snap(n + STEP / 2, np.round) + STEP, snap(w - STEP / 2, np.round) - STEP,
            snap(s - STEP / 2, np.round) - STEP, snap(e + STEP / 2, np.round) + STEP)]


def months(first, last):
    y, m = map(int, first.split("-"))
    while f"{y:04d}-{m:02d}" <= last:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def unpack(path, workdir):
    """The netCDF files a CDS download holds (it may be a zip of several)."""
    import zipfile
    if not zipfile.is_zipfile(path):
        return [path]
    with zipfile.ZipFile(path) as z:
        z.extractall(workdir)
        return [os.path.join(workdir, n) for n in z.namelist() if n.endswith(".nc")]


def opened(paths):
    ds = xr.merge([xr.open_dataset(p) for p in paths], compat="override")
    ds = ds.rename({"valid_time": "time"}) if "valid_time" in ds.dims else ds
    if "expver" in ds.dims:                  # ERA5 and ERA5T side by side: take whichever exists
        ds = ds.max("expver")
    return ds.drop_vars([v for v in ("number", "expver", "model_level", "hybrid", "level") if v in ds.coords], errors="ignore").squeeze()


def fetch(client, y, m, area, workdir):
    days = [f"{d:02d}" for d in range(1, 32)]
    last = (np.datetime64(f"{y + (m == 12):04d}-{m % 12 + 1:02d}-01") - np.timedelta64(1, "D")).astype(str)
    sfc, ml = os.path.join(workdir, "sfc.download"), os.path.join(workdir, "ml.download")
    client.retrieve("reanalysis-era5-single-levels", {
        "product_type": ["reanalysis"], "variable": ["surface_pressure", "mean_surface_downward_short_wave_radiation_flux",
        "mean_surface_downward_long_wave_radiation_flux", "mean_total_precipitation_rate"],
        "year": [f"{y:04d}"], "month": [f"{m:02d}"], "day": days, "time": [f"{h:02d}:00" for h in range(24)],
        "area": area, "data_format": "netcdf", "download_format": "unarchived"}, sfc)
    request = {"class": "ea", "stream": "oper", "type": "an", "levtype": "ml", "levelist": "137",
               "param": "130/131/132/133", "date": f"{y:04d}-{m:02d}-01/to/{last}", "time": "00/to/23/by/1",
               "grid": "0.25/0.25", "area": "/".join(f"{x:g}" for x in area), "data_format": "netcdf"}
    try:
        client.retrieve("reanalysis-era5-complete", dict(request, expver="1"), ml)
    except Exception:                        # the last months are ERA5T, expver 5
        client.retrieve("reanalysis-era5-complete", dict(request, expver="5"), ml)
    s = opened(unpack(sfc, os.path.join(workdir, "sfc")))
    a = opened(unpack(ml, os.path.join(workdir, "ml")))
    out = xr.Dataset({SURFACE[k]: s[k] for k in s.data_vars if k in SURFACE})
    out["airtemp"], out["spechum"] = a["t"], a["q"]
    out["windspd"] = np.hypot(a["u"], a["v"])
    return out


def write(ds, path):
    ds = ds.sortby("latitude", ascending=False).sortby("longitude")
    hours = ((ds.time.values - np.datetime64(EPOCH)) / np.timedelta64(1, "h")).astype("i4")
    out = xr.Dataset({k: (("time", "latitude", "longitude"), ds[k].values.astype("f4"), {"long_name": ATTRS[k][0], "units": ATTRS[k][1]})
                      for k in ATTRS}, coords={"time": ("time", hours, {"units": "hours since 1900-01-01 00:00:00.0",
                      "long_name": "time", "calendar": "gregorian"}), "latitude": ("latitude", ds.latitude.values.astype("f4"),
                      {"units": "degrees_north"}), "longitude": ("longitude", ds.longitude.values.astype("f4"), {"units": "degrees_east"})},
                     attrs={"History": f"acquire_era5.py {datetime.now(timezone.utc):%Y-%m-%d}: ERA5 from the CDS, model level 137 and surface"})
    if out.time.size % 24 or np.isnan(out.to_array().values).any():
        raise SystemExit(f"{path}: incomplete month or missing values")
    out.to_netcdf(path, encoding={"time": {"dtype": "i4"}})


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    p.add_argument("first", help="first month, YYYY-MM")
    p.add_argument("last", help="last month, YYYY-MM")
    a = p.parse_args()
    import cdsapi
    c = load_config(a.config)
    dom, project = c["domain"], c["project_dir"]
    raw_dir = os.path.join(project, "forcing", "raw_data")
    os.makedirs(raw_dir, exist_ok=True)
    area = grid_area(project, dom, raw_dir)
    client = cdsapi.Client()
    for y, m in months(a.first, a.last):
        path = os.path.join(raw_dir, f"domain_{dom}_ERA5_merged_{y:04d}{m:02d}.nc")
        if os.path.exists(path):
            continue
        with tempfile.TemporaryDirectory() as workdir:
            write(fetch(client, y, m, area, workdir), path)
        print(f"wrote {path}", flush=True)


if __name__ == "__main__":
    main()
