#!/usr/bin/env python3
"""Fetch a domain's hourly ERA5 from the Copernicus Climate Data Store into forcing/raw_data, one file a month.

The fields are those of the domain's 2008-2022 record, as the CWARHM ERA5 pull made them: temperature,
specific humidity and wind at the lowest model level (137, about 10 m) from reanalysis-era5-complete, and
surface pressure and the mean downward shortwave, longwave and total precipitation rates from
reanalysis-era5-single-levels, on the 0.25-degree grid.  Each month is written as
domain_<domain>_ERA5_merged_YYYYMM.nc with airtemp (K), spechum (kg kg-1), windspd (m s-1), airpres (Pa),
SWRadAtm and LWRadAtm (W m-2) and pptrate (kg m-2 s-1), time in hours since 1900-01-01 UTC at the end of
each hour, which remap_forcing.py then takes to the HRUs.  Months already in raw_data are skipped.

Several domains can share one request: the box is that of all their grids, and each domain's files are cut to its own.
Requests go to the CDS a quarter at a time (--chunk months, 3 being the most it takes; the months still ERA5T go one at a time), several
at once (--jobs), and their ids are kept in <out>/.era5_jobs.json, so a stopped run picks the queued jobs up again.

The grid is that of the files already in raw_data, else the cells the HRUs overlap and one more around.
Downloading needs a free CDS account, the ERA5 licence accepted on the dataset pages, and its key in ~/.cdsapirc
(url: https://cds.climate.copernicus.eu/api, key: <key>).  The model-level requests come off tape and can queue for days.

    ./acquire_era5.py 2004-10 2026-09 domains/wolverine.yaml domains/gulkana.yaml
"""

import argparse
import glob
import json
import os
import tempfile
import time
from datetime import datetime, timedelta, timezone

import geopandas as gpd
import numpy as np
import xarray as xr

from domain_config import load_config

STEP = 0.25                                  # deg, ERA5 grid
LATENCY = timedelta(days=130)                # months this recent may be ERA5T only
POLL = 120                                   # s between job status checks
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


def cut(ds, area):
    """The grid points of ds inside [north, west, south, east]."""
    n, w, s, e = area
    return ds.isel(latitude=((ds.latitude >= s - 1e-3) & (ds.latitude <= n + 1e-3)).values,
                   longitude=((ds.longitude >= w - 1e-3) & (ds.longitude <= e + 1e-3)).values)


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
    wrap = lambda d: d.assign_coords(longitude=(d.longitude + 180) % 360 - 180).sortby("longitude")   # the two datasets differ in 0-360 or -180-180
    ds = xr.merge([wrap(xr.open_dataset(p)) for p in paths], compat="override")
    ds = ds.rename({"valid_time": "time"}) if "valid_time" in ds.dims else ds
    if "expver" in ds.dims:                  # ERA5 and ERA5T side by side: take whichever exists
        ds = ds.max("expver")
    return ds.drop_vars([v for v in ("number", "expver", "model_level", "hybrid", "level") if v in ds.coords], errors="ignore").squeeze()


def sfc_request(y, months_, area):
    return {"product_type": ["reanalysis"], "variable": ["surface_pressure", "mean_surface_downward_short_wave_radiation_flux",
            "mean_surface_downward_long_wave_radiation_flux", "mean_total_precipitation_rate"],
            "year": [f"{y:04d}"], "month": [f"{m:02d}" for m in months_], "day": [f"{d:02d}" for d in range(1, 32)],
            "time": [f"{h:02d}:00" for h in range(24)], "area": area, "data_format": "netcdf", "download_format": "unarchived"}


def ml_request(y, months_, area, expver):
    last = (np.datetime64(f"{y + (months_[-1] == 12):04d}-{months_[-1] % 12 + 1:02d}-01") - np.timedelta64(1, "D")).astype(str)
    return {"class": "ea", "stream": "oper", "type": "an", "levtype": "ml", "levelist": "137", "param": "130/131/132/133",
            "date": f"{y:04d}-{months_[0]:02d}-01/to/{last}", "time": "00/to/23/by/1", "grid": "0.25/0.25",
            "area": "/".join(f"{x:g}" for x in area), "data_format": "netcdf", "expver": expver}


def chunks(first, last, size, today):
    """[(year, [months])] of the requests: `size` months aligned to the calendar, single months once ERA5T."""
    late = f"{today - LATENCY:%Y-%m}"
    groups = {}
    for y, m in months(first, last):
        groups.setdefault((y, (m - 1) // size) if f"{y:04d}-{m:02d}" <= late else (y, m, "T"), []).append(m)
    return [(k[0], ms) for k, ms in groups.items()]


def assemble(sfc, ml, workdir):
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


def store(job, files, workdir, areas):
    """Download a finished chunk and write its months for each domain."""
    ds = assemble(job["sfc"].download(os.path.join(workdir, "sfc.download")), job["ml"].download(os.path.join(workdir, "ml.download")), workdir)
    for dom, area in areas.items():
        for y, m in job["months"]:
            path = files(dom, y, m)
            if not os.path.exists(path):
                write(cut(ds, area).isel(time=((ds.time.dt.month == m) & (ds.time.dt.year == y)).values), path)
                print(f"wrote {path}", flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("first", help="first month, YYYY-MM")
    p.add_argument("last", help="last month, YYYY-MM")
    p.add_argument("config", nargs="+", help="domain YAMLs in domains/")
    p.add_argument("--chunk", type=int, default=3, choices=(1, 2, 3), help="months per request")
    p.add_argument("--jobs", type=int, default=3, help="requests in the queue at once")
    p.add_argument("--out", help="directory for the monthly files (default forcing/raw_data; one domain only)")
    a = p.parse_args()
    import cdsapi
    from ecmwf.datastores import Client
    cs = [load_config(f) for f in a.config]
    if a.out and len(cs) > 1:
        raise SystemExit("--out takes one domain")
    dirs = {c["domain"]: a.out or os.path.join(c["project_dir"], "forcing", "raw_data") for c in cs}
    areas = {c["domain"]: grid_area(c["project_dir"], c["domain"], os.path.join(c["project_dir"], "forcing", "raw_data")) for c in cs}
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
    area = [max(x[0] for x in areas.values()), min(x[1] for x in areas.values()),
            min(x[2] for x in areas.values()), max(x[3] for x in areas.values())]
    files = lambda dom, y, m: os.path.join(dirs[dom], f"domain_{dom}_ERA5_merged_{y:04d}{m:02d}.nc")
    url, key, _ = cdsapi.api.get_url_key_verify(None, None, None)
    client = Client(url=url, key=key)
    state_path = os.path.join(next(iter(dirs.values())), ".era5_jobs.json")
    saved = json.load(open(state_path)) if os.path.exists(state_path) else {}
    todo = [(y, [m for m in ms if not all(os.path.exists(files(d, y, m)) for d in dirs)]) for y, ms in chunks(a.first, a.last, a.chunk, datetime.now(timezone.utc).date())]
    todo = [(y, ms) for y, ms in todo if ms]
    keyof = lambda y, ms: f"{y:04d}-{ms[0]:02d}_{ms[-1]:02d}"
    pending, active = list(todo), {}

    def save():
        json.dump({k: {"sfc": j["sfc"].request_id, "ml": j["ml"].request_id, "expver": j["expver"]} for k, j in active.items()},
                  open(state_path, "w"))

    def submit_ml(y, ms, expver):
        return client.submit("reanalysis-era5-complete", ml_request(y, ms, area, expver))

    for y, ms in list(pending):                       # resume jobs of an earlier run
        k = keyof(y, ms)
        if k in saved:
            pending.remove((y, ms))
            active[k] = {"y": y, "ms": ms, "months": [(y, m) for m in ms], "expver": saved[k]["expver"],
                         "sfc": client.get_remote(saved[k]["sfc"]), "ml": client.get_remote(saved[k]["ml"])}
    while pending or active:
        while pending and len(active) < a.jobs and keyof(*pending[0]) not in active:
            y, ms = pending.pop(0)
            active[keyof(y, ms)] = {"y": y, "ms": ms, "months": [(y, m) for m in ms], "expver": "1",
                                    "sfc": client.submit("reanalysis-era5-single-levels", sfc_request(y, ms, area)),
                                    "ml": submit_ml(y, ms, "1")}
            print(f"submitted {keyof(y, ms)}", flush=True)
            save()
        for k, j in list(active.items()):
            try:
                st = j["st"] = {n: j[n].status for n in ("sfc", "ml")}
            except OSError as e:                      # the CDS is slow to answer; look again next time
                print(f"{k}: status unavailable ({type(e).__name__})", flush=True)
                if getattr(getattr(e, "response", None), "status_code", None) == 404:      # a job deleted at the CDS is not coming back
                    for n in ("sfc", "ml"):
                        try:
                            j[n].delete()
                        except OSError:
                            pass
                    pending.append((j["y"], j["ms"]))
                    del active[k]
                    save()
                continue
            if "rejected" in st.values():             # over the CDS's limit on a user's queued requests: try again later
                for n in ("sfc", "ml"):
                    j[n].delete()
                pending.append((j["y"], j["ms"]))
                del active[k]
                save()
            elif st["ml"] == "failed" and j["expver"] == "1":      # the months not in ERA5 yet are expver 5
                j["ml"], j["expver"] = submit_ml(j["y"], j["ms"], "5"), "5"
                save()
            elif "failed" in st.values():
                raise SystemExit(f"{k}: request failed: {st}")
            elif set(st.values()) == {"successful"}:
                with tempfile.TemporaryDirectory() as workdir:
                    store(j, files, workdir, areas)
                del active[k]
                save()
        if active or pending:
            print(f"{datetime.now():%H:%M} waiting: " + ", ".join(f"{k} {j['st']['sfc'][:3]}/{j['st']['ml'][:3]}" for k, j in active.items() if "st" in j), flush=True)
            time.sleep(POLL)
    if os.path.exists(state_path):
        os.remove(state_path)


if __name__ == "__main__":
    main()
