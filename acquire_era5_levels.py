#!/usr/bin/env python3
"""Fetch a domain's ERA5 pressure-level fields into forcing/raw_levels, one file a month, and ERA5's own surface
elevation of the same grid points.

remap_forcing.py reads the free-air temperature, humidity and pressure at each HRU's elevation from these (the
TopoSCALE method of Fiddes and Gruber, 2014), in place of the near-surface values of forcing/raw_data carried from the
height of ERA5's smoothed terrain.  The levels are the ERA5 pressure levels spanning the domains' HRU elevations in the
standard atmosphere, from BELOW m under the lowest to the first level ABOVE m over the highest, every EVERY hours from
00 UTC.  Each month is written as domain_<domain>_ERA5_levels_YYYYMM.nc with airtemp (K), spechum (kg kg-1) and height
(geopotential height, m) by time, level (hPa, falling), latitude and longitude, on the grid of raw_data.  The surface
elevation (m) goes to domain_<domain>_ERA5_orography.nc.  Months already in raw_levels are skipped.

raw_levels sits beside the raw_data the domain reads, so a seeded domain shares its source's, and the domains given
share each request, the box of all their grids.  Two sources hold the same fields:

  ncar  NCAR's copy (Research Data Archive d633000) read by OPeNDAP, a day and a field at a time, --workers at once,
        from the first month on.  No account and no queue, but it trails ERA5 by a few months.
  cds   The Copernicus Climate Data Store, from the last month back, as many months of a year in a request as it takes
        (LIMIT fields, in GRIB), --jobs queued at once; the job ids are kept in .era5_levels_jobs.json, so a stopped
        run picks its queued jobs up again.  Hours in its queue, but complete.  Needs acquire_era5.py's CDS account
        and key, and cfgrib.

The two can run side by side; each skips the months the other has written.

    ./acquire_era5_levels.py 2004-10 2026-09 domains/wolverine.yaml domains/gulkana.yaml
    ./acquire_era5_levels.py 2004-10 2026-09 domains/wolverine.yaml domains/gulkana.yaml --source cds
"""

import argparse
import calendar
import json
import os
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timezone

import geopandas as gpd
import numpy as np
import xarray as xr

from acquire_era5 import EPOCH, POLL, cut, grid_area, months, opened, unpack
from domain_config import load_config

LEVELS = (1000, 975, 950, 925, 900, 875, 850, 825, 800, 775, 750, 700, 650, 600, 550, 500, 450, 400, 350, 300)  # hPa
BELOW, ABOVE = 350.0, 400.0        # m beyond the HRU elevations the levels reach in the standard atmosphere
EVERY = 3                          # h between the fields
LIMIT = 60000                      # fields (variables x levels x times) the CDS takes in one request
G = 9.80665                        # m s-2
GRID = 0.25                        # deg
TRIES = 6                          # of a read from NCAR
PARAMS = ["temperature", "geopotential", "specific_humidity"]
ATTRS = {"airtemp": ("Temperature", "K"), "spechum": ("Specific humidity", "kg kg**-1"), "height": ("Geopotential height", "m")}
NCAR = "https://thredds.rda.ucar.edu/thredds/dodsC/files/g/d633000/"
NCAR_LEVELS = NCAR + "e5.oper.an.pl/{y:04d}{m:02d}/e5.oper.an.pl.128_{code}.ll025sc.{y:04d}{m:02d}{d:02d}00_{y:04d}{m:02d}{d:02d}23.nc"
NCAR_SURFACE = NCAR + "e5.oper.invariant/197901/e5.oper.invariant.128_129_z.ll025sc.1979010100_1979010100.nc"
NCAR_FIELDS = {"t": ("130_t", "T"), "z": ("129_z", "Z"), "q": ("133_q", "Q")}


def levels_dir(project):
    """raw_levels beside the raw_data the domain reads (a seeded domain's is a link to its source's)."""
    return os.path.join(os.path.dirname(os.path.realpath(os.path.join(project, "forcing", "raw_data"))), "raw_levels")


def levels_for(z_low, z_high):
    """The ERA5 pressure levels (hPa) whose standard-atmosphere height is over z_low - BELOW (m), up to the first at
    or over z_high + ABOVE."""
    h = lambda p: (1.0 - (p / 1013.25) ** (1.0 / 5.25588)) / 2.25577e-5
    return [l for k, l in enumerate(LEVELS) if h(l) > z_low - BELOW and (k == 0 or h(LEVELS[k - 1]) < z_high + ABOVE)]


def write(ds, path):
    """A month of t, q and z (m2 s-2) by time, level, latitude and longitude as a raw_levels file."""
    ds = ds.sortby("level", ascending=False).sortby("latitude", ascending=False).sortby("longitude")
    ds = ds.transpose("time", "level", "latitude", "longitude")
    hours = ((ds.time.values - np.datetime64(EPOCH)) / np.timedelta64(1, "h")).astype("i4")
    fields = {"airtemp": ds["t"].values, "spechum": ds["q"].values, "height": ds["z"].values / G}
    dims = ("time", "level", "latitude", "longitude")
    out = xr.Dataset({k: (dims, v.astype("f4"), {"long_name": ATTRS[k][0], "units": ATTRS[k][1]}) for k, v in fields.items()},
                     coords={"time": ("time", hours, {"units": "hours since 1900-01-01 00:00:00.0", "long_name": "time",
                             "calendar": "gregorian"}), "level": ("level", ds.level.values.astype("f4"), {"units": "hPa"}),
                             "latitude": ("latitude", ds.latitude.values.astype("f4"), {"units": "degrees_north"}),
                             "longitude": ("longitude", ds.longitude.values.astype("f4"), {"units": "degrees_east"})},
                     attrs={"History": f"acquire_era5_levels.py {datetime.now(timezone.utc):%Y-%m-%d}: ERA5 pressure levels"})
    y, m = int(str(ds.time.values[0])[:4]), int(str(ds.time.values[0])[5:7])
    if out.time.size != calendar.monthrange(y, m)[1] * 24 // EVERY or not np.isfinite(out.to_array().values).all():
        raise SystemExit(f"{path}: incomplete month or missing values")
    out.to_netcdf(path + ".part", encoding={"time": {"dtype": "i4"}})
    os.replace(path + ".part", path)
    print(f"{datetime.now():%H:%M} wrote {path}", flush=True)


def write_orography(zs, areas, oro):
    """ERA5's surface elevation (m, by latitude and longitude) cut to each domain."""
    for dom, area in areas.items():
        c = cut(zs.to_dataset(name="elevation"), area).sortby("latitude", ascending=False).sortby("longitude")
        c["elevation"].attrs = {"long_name": "ERA5 surface elevation", "units": "m"}
        c[["elevation"]].drop_vars([v for v in c.coords if v not in ("latitude", "longitude")]).to_netcdf(oro(dom))
        print(f"wrote {oro(dom)}", flush=True)


# ---- NCAR

def box(area):
    """The rows and the runs of columns of NCAR's grid (90 to -90 N, 0 to 359.75 E) inside [north, west, south, east]:
    two runs when the box holds the Greenwich meridian."""
    n, w, s, e = area
    i, j = lambda lat: int(round((90.0 - lat) / GRID)), lambda lon: int(round((lon % 360.0) / GRID))
    cols = [(j(w), j(e))] if j(w) <= j(e) else [(j(w), int(round(360.0 / GRID)) - 1), (0, j(e))]
    return (i(n), i(s)), cols


def ncar_read(url, name, index, rows, cols, coord=None):
    """A field's values at index (the leading dimensions) over the box, and the coordinate coord if asked."""
    from netCDF4 import Dataset
    for attempt in range(TRIES):
        try:
            with Dataset(url) as f:
                v = f[name]
                parts = [np.asarray(v[index + (slice(rows[0], rows[1] + 1), slice(a, b + 1))]) for a, b in cols]
                return np.concatenate(parts, axis=-1), (np.asarray(f[coord][:]) if coord else None)
        except (OSError, RuntimeError):
            if attempt == TRIES - 1:
                raise
            time.sleep(20 * (attempt + 1))


def ncar_day(task):
    """A day of one field on the levels, every EVERY hours: (time, level, latitude, longitude), levels as NCAR has them."""
    y, m, d, key, levels, rows, cols = task
    code, name = NCAR_FIELDS[key]
    v, c = ncar_read(NCAR_LEVELS.format(y=y, m=m, d=d, code=code), name, (slice(0, 24, EVERY), slice(None)), rows, cols, "level")
    return v[:, np.isin(c, levels)]


def ncar_has(y, m):
    """Whether NCAR holds the month through its last day."""
    d = calendar.monthrange(y, m)[1]
    try:
        urllib.request.urlopen(NCAR_LEVELS.format(y=y, m=m, d=d, code=NCAR_FIELDS["t"][0]) + ".dds", timeout=120).close()
        return True
    except urllib.error.HTTPError:
        return False


def from_ncar(a, levels, area, areas, files, oro):
    rows, cols = box(area)
    lat = 90.0 - GRID * np.arange(rows[0], rows[1] + 1)
    lon = np.concatenate([GRID * np.arange(a_, b_ + 1) for a_, b_ in cols])
    lon = (lon + 180.0) % 360.0 - 180.0
    if not all(os.path.exists(oro(d)) for d in areas):
        z, _ = ncar_read(NCAR_SURFACE, "Z", (0,), rows, cols)
        write_orography(xr.DataArray(z / G, coords={"latitude": lat, "longitude": lon}, dims=("latitude", "longitude")), areas, oro)
    with ProcessPoolExecutor(a.workers) as pool:
        for y, m in months(a.first, a.last):
            if all(os.path.exists(files(d, y, m)) for d in areas):
                continue
            if not ncar_has(y, m):
                print(f"{y:04d}-{m:02d} is not at NCAR yet; --source cds has it", flush=True)
                continue
            days = range(1, calendar.monthrange(y, m)[1] + 1)
            got = list(pool.map(ncar_day, [(y, m, d, k, levels, rows, cols) for k in NCAR_FIELDS for d in days]))
            t = np.datetime64(f"{y:04d}-{m:02d}-01") + np.arange(0, 24 * len(days), EVERY) * np.timedelta64(1, "h")
            dims = ("time", "level", "latitude", "longitude")
            ds = xr.Dataset({k: (dims, np.concatenate(got[n * len(days):(n + 1) * len(days)])) for n, k in enumerate(NCAR_FIELDS)},
                            coords={"time": t.astype("datetime64[ns]"), "level": np.sort(np.asarray(levels, dtype="f8")),
                                    "latitude": lat, "longitude": lon})
            for dom in areas:
                if not os.path.exists(files(dom, y, m)):
                    write(cut(ds, areas[dom]), files(dom, y, m))


# ---- CDS

def chunks(yms, n_levels):
    """[[(year, month)]] of the requests: the months of a calendar year, split to stay under LIMIT fields."""
    per_day = 24 // EVERY * len(PARAMS) * n_levels
    out = []
    for y, m in yms:
        days = calendar.monthrange(y, m)[1]
        if out and out[-1][0][0] == y and (sum(calendar.monthrange(*ym)[1] for ym in out[-1]) + days) * per_day <= LIMIT:
            out[-1].append((y, m))
        else:
            out.append([(y, m)])
    return out


def request(yms, area, levels):
    return {"product_type": ["reanalysis"], "variable": PARAMS, "pressure_level": [str(l) for l in levels],
            "year": [f"{yms[0][0]:04d}"], "month": sorted(f"{m:02d}" for _, m in yms), "day": [f"{d:02d}" for d in range(1, 32)],
            "time": [f"{h:02d}:00" for h in range(0, 24, EVERY)], "area": area, "data_format": "grib", "download_format": "unarchived"}


def orography_request(area):
    """ERA5's surface geopotential over the box, a time-invariant field."""
    return {"product_type": ["reanalysis"], "variable": ["geopotential"], "year": ["2000"], "month": ["01"], "day": ["01"],
            "time": ["00:00"], "area": area, "data_format": "netcdf", "download_format": "unarchived"}


def read_grib(path):
    ds = xr.open_dataset(path, engine="cfgrib", backend_kwargs={"indexpath": ""})
    ds = ds.assign_coords(longitude=(ds.longitude + 180) % 360 - 180).sortby("longitude")
    return ds.rename({"isobaricInhPa": "level"})


def from_cds(a, levels, area, areas, files, oro, state_path):
    import cdsapi
    from ecmwf.datastores import Client
    url, key, _ = cdsapi.api.get_url_key_verify(None, None, None)
    client = Client(url=url, key=key)
    saved = json.load(open(state_path)) if os.path.exists(state_path) else {}
    missing = lambda y, m: not all(os.path.exists(files(d, y, m)) for d in areas)
    pending = chunks([ym for ym in list(months(a.first, a.last))[::-1] if missing(*ym)], len(levels))
    if not all(os.path.exists(oro(d)) for d in areas):
        pending.insert(0, "orography")
    keyof = lambda ch: ch if ch == "orography" else f"{ch[0][0]:04d}-{ch[-1][1]:02d}_{ch[0][1]:02d}"
    active, cap = {}, a.jobs

    def save():
        json.dump({k: j["job"].request_id for k, j in active.items()}, open(state_path, "w"))

    def submit(ch):
        if ch == "orography":
            return client.submit("reanalysis-era5-single-levels", orography_request(area))
        return client.submit("reanalysis-era5-pressure-levels", request(ch, area, levels))

    def store(ch, job, workdir):
        if ch == "orography":
            write_orography(opened(unpack(job.download(os.path.join(workdir, "oro.download")), workdir))["z"] / G, areas, oro)
            return
        ds = read_grib(job.download(os.path.join(workdir, "levels.grib")))
        for dom in areas:
            for y, m in ch:
                if not os.path.exists(files(dom, y, m)):
                    write(cut(ds, areas[dom]).isel(time=((ds.time.dt.month == m) & (ds.time.dt.year == y)).values), files(dom, y, m))

    for ch in list(pending):                          # resume jobs of an earlier run
        if keyof(ch) in saved:
            pending.remove(ch)
            active[keyof(ch)] = {"ch": ch, "job": client.get_remote(saved[keyof(ch)])}
    while pending or active:
        while pending and len(active) < cap:
            ch = pending.pop(0)
            if ch != "orography" and not any(missing(*ym) for ym in ch):      # the other source wrote them meanwhile
                continue
            try:
                active[keyof(ch)] = {"ch": ch, "job": submit(ch)}
            except OSError as e:
                if "too large" in str(e) and len(ch) > 1:      # over the CDS's size limit after all: a month at a time
                    pending[:0] = [[ym] for ym in ch]
                    continue
                print(f"{keyof(ch)}: not submitted ({str(e).splitlines()[-1][:120]})", flush=True)
                pending.insert(0, ch)
                break
            save()
        for k, j in list(active.items()):
            try:
                st = j["st"] = j["job"].status
            except OSError as e:                      # the CDS is slow to answer; look again next time
                print(f"{k}: status unavailable ({type(e).__name__})", flush=True)
                if getattr(getattr(e, "response", None), "status_code", None) == 404:      # a job deleted at the CDS is not coming back
                    pending.insert(0, j["ch"])
                    del active[k]
                    save()
                continue
            if st == "rejected":                      # over the CDS's limit on a user's queued requests: queue fewer
                j["job"].delete()
                pending.insert(0, j["ch"])
                del active[k]
                cap = max(1, len(active))
                print(f"{k}: rejected by the CDS queue; {cap} request(s) at once from here", flush=True)
                save()
            elif st == "failed":
                raise SystemExit(f"{k}: request failed")
            elif st == "successful":
                with tempfile.TemporaryDirectory() as workdir:
                    store(j["ch"], j["job"], workdir)
                del active[k]
                save()
        if active or pending:
            n = {}
            for j in active.values():
                n[j.get("st", "?")] = n.get(j.get("st", "?"), 0) + 1
            print(f"{datetime.now():%H:%M} " + ", ".join(f"{v} {s}" for s, v in n.items()) + f"; {len(pending)} to submit", flush=True)
            time.sleep(POLL)
    if os.path.exists(state_path):
        os.remove(state_path)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("first", help="first month, YYYY-MM")
    p.add_argument("last", help="last month, YYYY-MM")
    p.add_argument("config", nargs="+", help="domain YAMLs in domains/")
    p.add_argument("--source", choices=("ncar", "cds"), default="ncar")
    p.add_argument("--workers", type=int, default=4, help="reads from NCAR at once")
    p.add_argument("--jobs", type=int, default=2, help="requests in the CDS queue at once")
    a = p.parse_args()
    cs = [load_config(f) for f in a.config]
    dirs = {c["domain"]: levels_dir(c["project_dir"]) for c in cs}
    areas = {c["domain"]: grid_area(c["project_dir"], c["domain"], os.path.join(c["project_dir"], "forcing", "raw_data")) for c in cs}
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
    area = [max(x[0] for x in areas.values()), min(x[1] for x in areas.values()),
            min(x[2] for x in areas.values()), max(x[3] for x in areas.values())]
    z = np.concatenate([gpd.read_file(os.path.join(c["project_dir"], "shapefiles", "catchment",
                                                   f"{c['domain']}_HRUs_elevation.shp")).elev_mean.values for c in cs])
    levels = levels_for(z.min(), z.max())
    print(f"levels {levels[0]} to {levels[-1]} hPa for HRUs at {z.min():.0f} to {z.max():.0f} m", flush=True)
    files = lambda dom, y, m: os.path.join(dirs[dom], f"domain_{dom}_ERA5_levels_{y:04d}{m:02d}.nc")
    oro = lambda dom: os.path.join(dirs[dom], f"domain_{dom}_ERA5_orography.nc")
    if a.source == "ncar":
        from_ncar(a, levels, area, areas, files, oro)
    else:
        from_cds(a, levels, area, areas, files, oro, os.path.join(next(iter(dirs.values())), ".era5_levels_jobs.json"))


if __name__ == "__main__":
    main()
