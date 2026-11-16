#!/usr/bin/env python3
"""The Glen factor multiplier f_A that ITS_LIVE speeds imply on a glacier with a fixed geometry, no SUMMA run needed.

The shallow-ice speed at f_A = 1 comes from the Copernicus GLO-30 surface and Millan et al. (2022) thickness on a 50 m
UTM grid (glen_factor.py's formula); the observed speed and the rules for a good year are glen_factor.py's: ice thicker
than 20 m, ITS_LIVE error under 10 m yr-1, a year counts where the ice median is at least --min-ratio times the median on
ice-free ground within 400 m (any RGI glacier is not ground), that noise taken off in quadrature, at least 3 years.
--smooth (m) is the Gaussian width the surface is smoothed over before its slope is taken.

    itslive_static.py gulkana RGI60-01.00570 RGI60-01.00571 RGI60-01.00569 RGI60-01.00561 RGI60-01.00556
    itslive_static.py wolverine RGI60-01.09162 RGI60-01.09216 RGI60-01.09061
    itslive_static.py lemon RGI60-01.01104 RGI60-01.01245 RGI60-01.01519
"""

import argparse
import glob
import os

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.warp import Resampling, reproject, transform_bounds
from scipy.ndimage import distance_transform_edt, gaussian_filter

EXT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "external")
RGI = os.path.join(EXT, "RGI_data", "nsidc0770_01.rgi60.Alaska", "01_rgi60_Alaska.shp")
URL = "/vsicurl/https://its-live-data.s3.amazonaws.com/velocity_mosaic/v2/annual/cog/ITS_LIVE_velocity_120m_RGI01A_{y}_v02_{f}.tif"
A0, N, RHO, G, YR = 2.4e-24, 3, 917.0, 9.80616, 365.25 * 86400
DX = 50.0
CRS = None  # UTM zone of the glaciers, set in main
DEM = "https://copernicus-dem-30m.s3.amazonaws.com/{t}/{t}.tif"


def dem_tiles(bounds):
    """Copernicus GLO-30 tiles over lon/lat bounds, the local copy where data/external has one."""
    out = []
    for lat in range(int(np.floor(bounds[1])), int(np.floor(bounds[3])) + 1):
        for lon in range(int(np.floor(bounds[0])), int(np.floor(bounds[2])) + 1):
            t = f"Copernicus_DSM_COG_10_{'N' if lat >= 0 else 'S'}{abs(lat):02d}_00_{'E' if lon >= 0 else 'W'}{abs(lon):03d}_00_DEM"
            local = os.path.join(EXT, "Copernicus_GLO30", t + ".tif")
            out.append(local if os.path.exists(local) else "/vsicurl/" + DEM.format(t=t))
    return out


def overlapping(paths, bounds):
    """The rasters whose extent meets lon/lat bounds."""
    out = []
    for p in paths:
        with rasterio.open(p) as r:
            b = transform_bounds(r.crs, "EPSG:4326", *r.bounds)
        if b[0] < bounds[2] and b[2] > bounds[0] and b[1] < bounds[3] and b[3] > bounds[1]:
            out.append(p)
    return out


def grid(outlines):
    """A 50 m UTM grid over the outlines and 1 km around them."""
    x0, y0, x1, y1 = outlines.to_crs(CRS).total_bounds
    x0, y0, x1, y1 = x0 - 1000, y0 - 1000, x1 + 1000, y1 + 1000
    return from_origin(x0, y1, DX, DX), (int((y1 - y0) / DX), int((x1 - x0) / DX))


def onto(paths, transform, shape, resampling, nodata=None):
    out = np.full(shape, np.nan)
    for p in paths:
        with rasterio.open(p) as r:
            part = np.full(shape, np.nan)
            reproject(rasterio.band(r, 1), part, dst_transform=transform, dst_crs=CRS, dst_nodata=np.nan,
                      resampling=resampling, src_nodata=r.nodata if nodata is None else nodata)
            out = np.where(np.isfinite(part), part, out)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("region")
    p.add_argument("ids", nargs="+", help="RGI 6.0 ids")
    p.add_argument("--first", type=int, default=2005)
    p.add_argument("--last", type=int, default=2022)
    p.add_argument("--smooth", type=float, default=0.0)
    p.add_argument("--min-ratio", type=float, default=2.5)
    a = p.parse_args()
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
    rgi = gpd.read_file(RGI)
    mine = rgi[rgi.RGIId.isin(a.ids)].set_index("RGIId").loc[a.ids]
    global CRS
    CRS = mine.estimate_utm_crs()
    transform, shape = grid(mine)
    bounds = transform_bounds(CRS, "EPSG:4326", transform.c, transform.f - shape[0] * DX, transform.c + shape[1] * DX, transform.f)
    all_ice = rasterize(rgi.cx[bounds[0]:bounds[2], bounds[1]:bounds[3]].to_crs(CRS).geometry, shape, transform=transform) == 1
    surf = onto(dem_tiles(bounds), transform, shape, Resampling.average)
    millan = overlapping(glob.glob(os.path.join(EXT, "Thickness_data", "RGI-[12]", "THICKNESS_*.tif")), bounds)
    thick = np.nan_to_num(onto(millan, transform, shape, Resampling.average))
    s = gaussian_filter(surf, a.smooth / DX) if a.smooth > 0 else surf
    gy, gx = np.gradient(s, DX)
    u = 2 * A0 / (N + 1) * (RHO * G) ** N * thick ** (N + 1) * np.hypot(gx, gy) ** N * YR
    obs = {}
    for y in range(a.first, a.last + 1):
        try:
            obs[y] = [onto([URL.format(y=y, f=f)], transform, shape, Resampling.nearest) for f in ("v", "v_error")]
        except rasterio.errors.RasterioIOError:
            continue
    for rid, g in mine.iterrows():
        mask = rasterize(gpd.GeoSeries([g.geometry], crs=rgi.crs).to_crs(CRS), shape, transform=transform) == 1
        ground = ~all_ice & (distance_transform_edt(~mask) * DX <= 400.0)
        used_o, used_m, lines = [], [], []
        for y, (v, e) in obs.items():
            ok = mask & (thick > 20) & np.isfinite(v) & (e < 10) & np.isfinite(u)
            floor = np.nanmedian(v[ground & np.isfinite(v)])
            if not ok.any():
                continue
            r = np.median(v[ok]) / floor
            if r >= a.min_ratio:
                used_o.append(np.sqrt(np.maximum(v[ok] ** 2 - floor ** 2, 0))); used_m.append(u[ok])
            lines.append(f"{y}:{r:.1f}{'*' if r >= a.min_ratio else ''}")
        name = g.Name if isinstance(g.Name, str) else rid
        head = f"{name:<22}{g.Area:6.1f} km2  ice>20 m {int((mask & (thick > 20)).sum() * DX * DX / 1e6 * 10) / 10:5.1f} km2"
        if len(used_o) >= 3:
            o, m = np.concatenate(used_o), np.concatenate(used_m)
            print(f"{head}  {len(used_o):2d} years  obs {np.median(o):5.1f}  SIA {np.median(m):5.1f} m/yr  f_A {np.median(o) / np.median(m):.2f}")
        else:
            print(f"{head}  {len(used_o):2d} years  f_A none")
        print("    ratio by year (* counts): " + " ".join(lines))


if __name__ == "__main__":
    main()
