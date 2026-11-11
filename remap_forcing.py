#!/usr/bin/env python3
"""Remap a domain's gridded ERA5 (forcing/raw_data and forcing/raw_levels) to its HRUs as SUMMA forcing
(forcing/SUMMA_input).

Each HRU takes the mean of the ERA5 cells it overlaps, weighted by the overlap area: the 0.25-degree cell
of each grid point is intersected with the HRU polygons of shapefiles/catchment/<domain>_HRUs_elevation.shp
in an equal-area projection.  Shortwave, precipitation and wind are the cells' surface fields.  Air temperature,
pressure and humidity are the free air's at the HRU's elev_mean, read from each cell's column of pressure levels
(acquire_era5_levels.py; the TopoSCALE method of Fiddes and Gruber, 2014): linear in geopotential height between the
two levels around the HRU, temperature, the logarithm of pressure and relative humidity alike, and linear in time
between the levels' fields.  Only
levels over ERA5's own surface (CLEAR m and more) count, the others being extrapolated from its near-surface air; an
HRU under the lowest of them continues the lowest two.  Longwave is the cell's at its sky emissivity, by the fourth
power of the free-air temperature at the HRU over that at the cell's surface elevation.  With wind_climatology in the
YAML (acquire_climatology.py), the wind is scaled by month to the climatology's mean over the HRU, over the run's mean
of the cell-weighted wind for that month.  With precip_climatology
in the YAML (acquire_climatology.py), precipitation is scaled by the HRU's mean climatology over the same weighting
of the cells' mean, the climatology's pattern within the ERA5 cells.  Every month of raw_data is written, one file per month, with the names
the rest of the pipeline reads.  Units and time (hours since 1900-01-01 UTC) pass through.  remap.csv keeps the
free air's mean lapse rate over the HRUs' elevations by calendar month, which build_cases.py gives SUMMA to carry
the temperature from an HRU to its domains, and the precipitation and wind ratios.

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

from acquire_era5_levels import levels_dir
from domain_config import load_config

VARS = ("airpres", "LWRadAtm", "SWRadAtm", "pptrate", "airtemp", "spechum", "windspd")
HALF = 0.125                       # deg, half an ERA5 cell
CLEAR = 0.0                        # m over ERA5's surface from which a pressure level counts as free air
SPAN = 300.0                       # m, least height over which the free-air lapse rate is taken
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


def cell_elevation(path, lat, lon):
    """(lat, lon) ERA5 surface elevation of the grid points, m."""
    with Dataset(path) as f:
        if not (np.allclose(f["latitude"][:], lat, atol=1e-4) and np.allclose(f["longitude"][:], lon, atol=1e-4)):
            raise SystemExit(f"{path} is not on the grid of raw_data")
        return np.asarray(f["elevation"][:], dtype="f8")


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


def wind_ratio(path, hrus, raw, w):
    """(13, hru) by calendar month (row 0 unused): each HRU's mean of the monthly wind climatology (one band a month)
    over the overlap-weighted ERA5 wind's mean for that month over the raw files."""
    with rasterio.open(path) as r:
        transform = r.transform
        clim = np.array([[raster_mean(np.where(b.mask, np.nan, b.data * sc + of), transform, g)
                          for g in hrus.to_crs(4326).geometry]
                         for b, sc, of in zip((r.read(k, masked=True).astype("f8") for k in range(1, 13)), r.scales, r.offsets)])
    total, count = np.zeros((13, len(hrus))), np.zeros(13)
    for path in raw:
        with Dataset(path) as src:
            month = np.array([d.month for d in num2date(src["time"][:], src["time"].units)])
            u = np.einsum("tij,kij->tk", np.asarray(src["windspd"][:], dtype="f8"), w)
        for m in np.unique(month):
            total[m] += u[month == m].sum(axis=0)
            count[m] += (month == m).sum()
    ratio = np.ones((13, len(hrus)))
    ratio[1:] = clim / (total[1:] / count[1:, None])
    return ratio


def relhum(q, p, t):
    """Relative humidity (-) from specific humidity, pressure (Pa) and temperature (K), as SUMMA's SPHM2RELHM."""
    e_sat = SATVPFRZ * np.exp(17.27 * (t - TFREEZE) / (237.30 + t - TFREEZE))
    return q * p / (e_sat * (W_RATIO + q * (1.0 - W_RATIO)))


def spechum(rh, p, t):
    """Specific humidity (kg kg-1) from relative humidity, pressure (Pa) and temperature (K), as SUMMA's RELHM2SPHM."""
    e = rh * SATVPFRZ * np.exp(17.27 * (t - TFREEZE) / (237.30 + t - TFREEZE))
    return e * W_RATIO / (p - (1.0 - W_RATIO) * e)


def column(h, z, floor):
    """Carries a (time, level) profile to height z (m): linear in the geopotential height h (time, level, rising)
    between the two levels around z, of those over floor (m); beyond them, along the nearest two."""
    nl, rows = h.shape[1], np.arange(h.shape[0])
    above = h > floor
    first = np.minimum(np.where(above.any(axis=1), np.argmax(above, axis=1), nl - 2), nl - 2)
    up = np.clip((h <= z).sum(axis=1), first + 1, nl - 1)
    f = (z - h[rows, up - 1]) / (h[rows, up] - h[rows, up - 1])
    return lambda x: x[rows, up - 1] + f * (x[rows, up] - x[rows, up - 1])


def read_levels(path, after, hours):
    """A month of pressure levels at hours (h since 1900): temperature (K), relative humidity (-) and height (m) by
    (time, level, lat, lon), and the logarithm of the levels' pressure (Pa).  Linear in time between the file's
    fields, the first of the next month's file (after, if there is one) closing the month; held past the last."""
    names = ("airtemp", "spechum", "height")
    with Dataset(path) as f:
        at = np.asarray(f["time"][:], dtype="f8")
        t, q, h = (np.asarray(f[v][:], dtype="f8") for v in names)
        p = np.asarray(f["level"][:], dtype="f8") * 100.0
    if after:
        with Dataset(after) as f:
            at = np.append(at, f["time"][0])
            t, q, h = (np.concatenate([x, np.asarray(f[v][:1], dtype="f8")]) for x, v in zip((t, q, h), names))
    if hours[0] < at[0] or hours[-1] >= at[-1] + (at[1] - at[0]):
        raise SystemExit(f"{path} does not hold the hours of raw_data")
    k = np.clip(np.searchsorted(at, hours, side="right") - 1, 0, len(at) - 2)
    f = np.clip((hours - at[k]) / (at[k + 1] - at[k]), 0.0, 1.0)[:, None, None, None]
    step = lambda x: x[k] + f * (x[k + 1] - x[k])
    return {"t": step(t), "rh": step(relhum(q, p[None, :, None, None], t)), "h": step(h), "lnp": np.log(p)}


def to_hru(f, lev, w, zs, z):
    """The month's forcing (time, hru) from the cells' surface fields f (time, lat, lon) and pressure levels lev,
    for HRUs at z (m) with cell weights w over cells at zs (m)."""
    out = {name: np.einsum("tij,kij->tk", f[name], w) for name in ("SWRadAtm", "pptrate", "windspd")}
    t, p, rh, lw = (np.zeros((len(f["LWRadAtm"]), len(z))) for _ in range(4))
    for k, i, j in zip(*np.nonzero(w)):
        h = lev["h"][:, :, i, j]
        hru, cell = column(h, z[k], zs[i, j] + CLEAR), column(h, zs[i, j], zs[i, j] + CLEAR)
        tk = hru(lev["t"][:, :, i, j])
        t[:, k] += w[k, i, j] * tk
        p[:, k] += w[k, i, j] * np.exp(hru(np.broadcast_to(lev["lnp"], h.shape)))
        rh[:, k] += w[k, i, j] * np.clip(hru(lev["rh"][:, :, i, j]), 0.01, 1.0)
        lw[:, k] += w[k, i, j] * f["LWRadAtm"][:, i, j] * (tk / cell(lev["t"][:, :, i, j])) ** 4
    return {**out, "airtemp": t, "airpres": p, "spechum": spechum(rh, p, t), "LWRadAtm": lw}


def free_air_lapse(lev, w, zs, z_low, z_high):
    """(time,) temperature decrease with height (K m-1) of the free air between z_low and z_high (m), over cell weights w (lat, lon)."""
    d = np.zeros(lev["h"].shape[0])
    for i, j in zip(*np.nonzero(w)):
        h, t = lev["h"][:, :, i, j], lev["t"][:, :, i, j]
        d += w[i, j] * (column(h, z_low, zs[i, j] + CLEAR)(t) - column(h, z_high, zs[i, j] + CLEAR)(t))
    return d / (z_high - z_low)


def remap(path, levels, after, out, w, zs, hrus, ratio, wind, span):
    """Write the month's forcing; returns its months (time,) and free-air lapse rate (time,) over span (m, low and high)."""
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
        lev = read_levels(levels, after, np.asarray(src["time"][:], dtype="f8"))
        f = to_hru({name: np.asarray(src[name][:], dtype="f8") for name in VARS}, lev, w, zs, hrus.elev_mean.values)
        f["pptrate"] = f["pptrate"] * ratio[None, :]
        f["windspd"] = f["windspd"] * wind[month]
        for name in VARS:
            s = src[name]
            v = dst.createVariable(name, "f8" if name == "airtemp" else "f4", ("time", "hru"), fill_value=FILL)
            v.setncatts({k: s.getncattr(k) for k in ("long_name", "units") if k in s.ncattrs()})
            v[:] = f[name]
        v = dst.createVariable("data_step", "i8")
        v.setncatts({"long_name": "data step length in seconds", "units": "s"})
        v.assignValue(3600)
        dst.setncatts({"Conventions": "CF-1.6", "Source": f"remap_forcing.py, area-weighted from {os.path.basename(path)}"})
    basin = np.einsum("k,kij->ij", hrus.HRU_area.values / hrus.HRU_area.sum(), w)
    return month, free_air_lapse(lev, basin, zs, *span)


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
    levels = levels_dir(project)
    level_file = lambda path: os.path.join(levels, os.path.basename(path).replace("_ERA5_merged_", "_ERA5_levels_"))
    if not all(os.path.exists(level_file(path)) for path in raw):
        raise SystemExit(f"{levels} lacks months of raw_data; run acquire_era5_levels.py first")
    zs = cell_elevation(os.path.join(levels, f"domain_{dom}_ERA5_orography.nc"), lat, lon)
    z = hrus.elev_mean.values
    span = (z.min(), z.max()) if z.max() - z.min() >= SPAN else (z.mean() - SPAN / 2, z.mean() + SPAN / 2)
    print("ERA5 surface under each HRU (m):", np.round(np.sum(w * zs, axis=(1, 2))), "HRUs at", np.round(z))
    ratio = precip_ratio(c["precip_climatology"], hrus, lat, lon, w) if "precip_climatology" in c else np.ones(len(hrus))
    print("precipitation ratio by HRU:", np.round(ratio, 3))
    wind = wind_ratio(c["wind_climatology"], hrus, raw, w) if "wind_climatology" in c else np.ones((13, len(hrus)))
    print("wind ratio by HRU, January and July:", np.round(wind[1], 2), np.round(wind[7], 2))
    out_dir = os.path.join(project, "forcing", "SUMMA_input")
    os.makedirs(out_dir, exist_ok=True)
    total, count = np.zeros(13), np.zeros(13)
    for path, after in zip(raw, raw[1:] + [None]):
        month, lapse = remap(path, level_file(path), after and level_file(after),
                             os.path.join(out_dir, f"{dom}_ERA5_remapped_{os.path.basename(path)}"), w, zs, hrus, ratio, wind, span)
        np.add.at(total, month, lapse)
        np.add.at(count, month, 1)
    lapse = total[1:] / count[1:]  # by calendar month
    print(f"free-air lapse rate {span[0]:.0f}-{span[1]:.0f} m by month (K/km):", np.round(-1000 * lapse, 2))
    with open(os.path.join(out_dir, "remap.csv"), "w") as f:
        f.write("lapse_rate_K_per_km," + ",".join(f"{-1000 * x:.2f}" for x in lapse) + "\n")
        f.write("precip_ratio," + ",".join(f"{r:.4f}" for r in ratio) + "\n")
        for k in range(len(hrus)):
            f.write(f"wind_ratio_hru{k + 1}," + ",".join(f"{x:.3f}" for x in wind[1:, k]) + "\n")
    print(f"{len(raw)} months remapped to {out_dir}")


if __name__ == "__main__":
    main()
