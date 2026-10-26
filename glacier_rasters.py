#!/usr/bin/env python3
"""Make the glacier rasters of a SYMFLUENCE domain on its surface DEM grid.

From the global glacier products (each downloaded by hand, see README.md) writes, in attributes/glaciers:

  domain_<name>_domain_type.tif       1 upland, 2 accumulation, 3 clean ablation, 4 debris ablation
  domain_<name>_rgi_id.tif            RGI 6.0 id as region*100000 + number, 0 off glacier
  domain_<name>_debris_thickness.tif  debris thickness (m), non-zero only where the type is 4

and in attributes/elevation/dem domain_<name>_glacier_elv.tif, the glacier surface: the DEM, with the start
surface of the glacier usgs_outline names (its survey DEM, or its survey DEMs interpolated in time to its date,
each levelled to the millan_reference survey; the change from the DEM carried smoothly over cells none covers);
and domain_<name>_bedrock_elv.tif, Millan's reference surface (the survey DEM millan_reference names, levelled
by usgs_datum, else the glacier surface) less his thickness, and that surface itself where the reference outline
has no ice; both again as *_elv_utm.tif on the flow model's UTM grid, with Millan sampled straight onto it. The
start outline is that survey's, or between the two usgs_outline lists. Where later_outline names a later
survey of that glacier, the bed under the ice lost between the two outlines is the surface of the ArcticDEM strips
after it (acquire_arcticdem.py, each levelled to the DEM on the ground around the glacier), and that change of
the bed is carried harmonically over the glacier within reach (250 m) of them, to nothing at the ice-free ground.

Glacier outlines are RGI 6.0, replaced by the Herreid and Pellicciotti (2020) outline where it has one, and by a
USGS survey outline (McNeil et al. 2019, doi:10.5066/P9R8BP3K) where the YAML's usgs_outline names one. Their
ablation zones (buffered 50 m, clipped to the glacier) set the ablation area; a glacier without one uses Zmed
as its equilibrium line. Debris is their debris cover, never in the accumulation zone, and every glacier keeps
at least its highest cells as accumulation. Debris thickness is Rounce et al. (2021), nearest neighbour, with
thicknesses at or below --min-debris (0.04 m) raised to it (Herreid 2021; Rounce et al. 2018). Glacier
thickness is Millan et al. (2022), bilinear over his cells, zero off the outlines and filled from the nearest
Millan cell where an outline reaches past it. It also prints each glacier's lateral moraine width, the mean thinnest width of its
debris polygons, for latMoraineWidth.

    ./glacier_rasters.py domains/wolverine.yaml
"""

import argparse
import glob
import os
import re
import shutil

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask, shapes
from rasterio.mask import mask
from rasterio.merge import merge
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, calculate_default_transform, reproject
from scipy.interpolate import griddata
from scipy.ndimage import distance_transform_edt
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import spsolve
from shapely.affinity import rotate
from shapely.geometry import Point, box, shape
from shapely.ops import unary_union

from domain_config import load_config

UPLAND, ACCUMULATION, CLEAN_ABLATION, DEBRIS_ABLATION = 1, 2, 3, 4
HERE = os.path.dirname(os.path.abspath(__file__))


def elevation_polygon(src, geometry, z, side):
    """The part of a glacier above (side 'high') or below ('low') elevation z, z held within its elevations."""
    image = mask(src, [geometry], crop=True)
    out_image, out_transform = image[0][0], image[1]
    valid = out_image[out_image > 0]
    if side == "high":
        selected = (out_image > min(z, valid.max())) & (out_image > 0)
    else:
        selected = (out_image < max(z, valid.min())) & (out_image > 0)
    polygons = [shape(g) for g, v in shapes(selected.astype(np.int16), transform=out_transform) if v == 1]
    return unary_union(polygons) if polygons else None


def thinnest_width(polygon):
    """Thinnest width of a polygon's convex hull (m in a projected CRS), the largest part of a multipolygon."""
    if polygon.geom_type == "MultiPolygon":
        polygon = max(polygon.geoms, key=lambda p: p.area)
    hull = polygon.convex_hull
    coords = np.array(hull.exterior.coords)
    width = np.inf
    for p1, p2 in zip(coords[:-1], coords[1:]):
        angle = np.degrees(np.arctan2(p2[1] - p1[1], p2[0] - p1[0]))
        bounds = rotate(hull, -angle, origin=(0, 0)).bounds
        width = min(width, bounds[3] - bounds[1])
    return width


def mosaic_to_dem(files, target_crs, dem_shape, dem_transform, tmp_dir):
    """Mosaic rasters reprojected to the DEM's CRS, and interpolate them nearest-neighbour onto the DEM grid."""
    os.makedirs(tmp_dir, exist_ok=True)
    try:
        reprojected = []
        for n, path in enumerate(files):
            with rasterio.open(path) as src:
                transform, width, height = calculate_default_transform(src.crs, target_crs, src.width, src.height, *src.bounds)
                meta = src.meta.copy()
                meta.update({"crs": target_crs, "transform": transform, "width": width, "height": height})
                out = os.path.join(tmp_dir, f"reprojected_{n}.tif")
                with rasterio.open(out, "w", **meta) as dst:
                    for i in range(1, src.count + 1):
                        reproject(source=rasterio.band(src, i), destination=rasterio.band(dst, i),
                                  src_transform=src.transform, src_crs=src.crs, dst_transform=transform,
                                  dst_crs=target_crs, resampling=Resampling.nearest)
            reprojected.append(out)
        sources = [rasterio.open(p) for p in reprojected]
        mosaic, mosaic_transform = merge(sources)
        for s in sources:
            s.close()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # subset the mosaic to the DEM's bounds
    dem_box = box(*rasterio.transform.array_bounds(dem_shape[0], dem_shape[1], dem_transform))
    mosaic_box = box(*rasterio.transform.array_bounds(mosaic.shape[1], mosaic.shape[2], mosaic_transform))
    minx, miny, maxx, maxy = dem_box.intersection(mosaic_box).bounds
    col0, row0 = ~mosaic_transform * (minx, maxy)
    col1, row1 = ~mosaic_transform * (maxx, miny)
    subset = mosaic[0][int(row0):int(row1), int(col0):int(col1)]
    subset_transform = from_bounds(minx, miny, maxx, maxy, subset.shape[1], subset.shape[0])

    rows, cols = np.indices(dem_shape)
    x, y = rasterio.transform.xy(dem_transform, rows, cols)
    src_rows, src_cols = np.indices(subset.shape)
    sx, sy = rasterio.transform.xy(subset_transform, src_rows, src_cols)
    points = np.vstack([np.array(sx).ravel(), np.array(sy).ravel()]).T
    return griddata(points, subset.ravel(), (np.array(x).ravel(), np.array(y).ravel()), method="nearest").reshape(dem_shape)


def harmonic_fill(values, known, region):
    """values with the region cells not known replaced by the harmonic surface through the known cells and 0
    outside the region (4-neighbour Laplace)."""
    solve = region & ~known
    n = int(solve.sum())
    out = np.where(known, values, 0.0)
    if n == 0:
        return out
    index = np.full(values.shape, -1)
    index[solve] = np.arange(n)
    rows, cols, vals, rhs = [], [], [], np.zeros(n)
    for (r, c), i in zip(np.argwhere(solve), index[solve]):
        rows.append(i); cols.append(i); vals.append(4.0)
        for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if not (0 <= rr < values.shape[0] and 0 <= cc < values.shape[1]):
                continue
            if solve[rr, cc]:
                rows.append(i); cols.append(index[rr, cc]); vals.append(-1.0)
            else:
                rhs[i] += out[rr, cc]
    out[solve] = spsolve(csr_matrix((vals, (rows, cols)), shape=(n, n)), rhs)
    return out


def decimal_year(date):
    """A YYYY/MM/DD or YYYYMMDD date as a decimal year."""
    t = pd.Timestamp(str(date).replace("/", "-") if "/" in str(date) else f"{str(date)[:4]}-{str(date)[4:6]}-{str(date)[6:8]}")
    return t.year + (t.dayofyear - 0.5) / (366 if t.is_leap_year else 365)


def grid_xy(grid, shape):
    """Cell-centre coordinates (km, about the grid's centre) of a geographic or projected grid."""
    rows, cols = np.indices(shape)
    x, y = grid.transform * (cols + 0.5, rows + 0.5)
    x, y = x - x.mean(), y - y.mean()
    if grid.crs.is_geographic:
        lat = grid.transform.f + grid.transform.e * shape[0] / 2
        return x * 111.32 * np.cos(np.radians(lat)), y * 111.32
    return x / 1000.0, y / 1000.0


def survey_on_grid(dem, grid, outlines, path, buffer=1000.0, anchor=None, around=None, offset=None):
    """A survey DEM's mean on each grid cell inside the outlines, the fraction of each cell it covers, and its mean
    on the ground within buffer (m) of them (of around, if given), all levelled: by offset (m) if given, else to
    the DEM by their median difference on that ground,
    or to anchor (another survey's levelled ground means) by a plane and an elevation term fitted on the ground
    both cover where it slopes under 20 degrees (2 m read; outliers beyond 3 NMAD dropped)."""
    with rasterio.open(path) as s:
        f = max(1, int(2.0 / abs(s.res[0])))  # surveys finer than 2 m are read at 2 m
        z = s.read(1, masked=True, out_shape=(s.height // f, s.width // f),
                   resampling=Resampling.average).astype(np.float64).filled(np.nan)
        t = s.transform * s.transform.scale(s.width / z.shape[1], s.height / z.shape[0])
        on_ice = geometry_mask(list(outlines.to_crs(s.crs).geometry), transform=t, invert=True, out_shape=z.shape)
        near = geometry_mask(list((outlines if around is None else around).to_crs(s.crs).buffer(buffer)), transform=t,
                             invert=True, out_shape=z.shape)
        means = {}
        for key, keep in (("ice", on_ice), ("ground", near & ~on_ice), ("cover", None)):
            out = np.full(dem.shape, np.nan)
            values = np.isfinite(z).astype(np.float64) if keep is None else np.where(keep, z, np.nan)
            reproject(values, out, src_transform=t, src_crs=s.crs, src_nodata=np.nan,
                      dst_transform=grid.transform, dst_crs=grid.crs, dst_nodata=np.nan, resampling=Resampling.average)
            means[key] = out
    ground = means["ground"]
    if anchor is None and offset is not None:
        both = np.isfinite(ground)
        fit, how = np.full(dem.shape, float(offset)), "usgs_datum"
    elif anchor is None:
        both = np.isfinite(ground) & np.isfinite(dem)
        fit, how = np.full(dem.shape, np.median((dem - ground)[both])), "median to the DEM"
    else:
        x, y = grid_xy(grid, dem.shape)
        terms = lambda z: np.stack([np.ones(z.shape), x, y, (z - 1500.0) / 100.0], -1)  # (ny, nx, 4)
        gy, gx = np.gradient(anchor, *cell_size(grid, dem.shape)[::-1])
        both = np.isfinite(anchor) & np.isfinite(ground) & (np.degrees(np.arctan(np.hypot(gx, gy))) < 20)
        d, keep = anchor - ground, both.copy()
        for _ in range(3):
            a, *_ = np.linalg.lstsq(terms(ground)[keep], d[keep], rcond=None)
            res = d[both] - terms(ground)[both] @ a
            nmad = 1.4826 * np.median(np.abs(res - np.median(res)))
            keep[both] = np.abs(res) < 3 * nmad
        fit = terms(np.where(np.isfinite(means["ice"]), means["ice"], np.where(np.isfinite(ground), ground, dem))) @ a
        how = (f"plane {a[1]:+.2f} m/km E {a[2]:+.2f} m/km N, {a[3]:+.2f} m/100 m, residual NMAD {nmad:.1f} m, "
               "to the anchor")
    print(f"{os.path.basename(path)}: {np.nanmedian(fit[both]):+.1f} m ({how}) on {both.sum()} ground cells")
    return means["ice"] + fit, np.nan_to_num(means["cover"]), ground + fit


def survey_surface(dem, glacier, grid, outlines, paths, date=None, min_cover=0.5, anchor=None, around=None,
                   offset=None, dhdt=None):
    """The DEM with the survey DEMs' surface on the glacier cells they cover by at least min_cover, linear in time
    between the nearest surveys before and after date (decimal year) that cover each cell, or the nearer one
    where only one side does; with dhdt (m/yr on the grid), each survey is first carried to date at that rate.
    The change from the DEM is carried harmonically onto the glacier cells none covers, to nothing at the ice-free
    ground. Every survey is levelled to anchor (levelled ground means), else the first by offset or to the DEM and the rest to it. Returns the surface and the levelled ground of the first survey."""
    zs, years = [], []
    for path in paths:
        z, cover, ground = survey_on_grid(dem, grid, outlines, path, anchor=anchor, around=around, offset=offset)
        anchor = ground if anchor is None else anchor
        years.append(decimal_year(re.search(r"(\d{8})", os.path.basename(path)).group(1)))
        if dhdt is not None and date is not None:
            z = z + dhdt * (date - years[-1])
        zs.append(np.where(cover >= min_cover, z, np.nan))
    zs, years = np.array(zs), np.array(years)
    date = years[0] if date is None else date
    have = np.isfinite(zs)
    before = np.where(have & (years[:, None, None] <= date), years[:, None, None], -np.inf).argmax(0)
    after = np.where(have & (years[:, None, None] > date), years[:, None, None], np.inf).argmin(0)
    hb = np.take_along_axis(have, before[None], 0)[0] & (years[before] <= date)
    ha = np.take_along_axis(have, after[None], 0)[0] & (years[after] > date)
    zb, za = (np.take_along_axis(zs, k[None], 0)[0] for k in (before, after))
    w = np.where(hb & ha, (date - years[before]) / np.where(hb & ha, years[after] - years[before], 1), 0.0)
    surf = np.where(hb & ha, zb + w * (za - zb), np.where(hb, zb, za))
    known = glacier & np.isfinite(surf)
    print(f"surface at {date:.2f}: {(known & hb & ha).sum()} of {glacier.sum()} glacier cells between two surveys, "
          f"{(known & ~(hb & ha)).sum()} from one")
    change = harmonic_fill(np.where(known, surf - dem, 0.0), known, glacier)
    return np.where(glacier, dem + change, dem), anchor


def start_outline(usgs, surveys):
    """The benchmark glacier's outline at the start (usgs_outline date): that survey's, or between the two
    outlines usgs_outline lists, as the zero contour of their signed distances (10 m grid) blended with the
    weight that makes its area linear in time between theirs."""
    if "outlines" not in usgs:
        return surveys[surveys["Date"] == usgs["date"]].geometry.union_all()
    (da, db), t = usgs["outlines"], decimal_year(usgs["date"])
    a, b = (surveys[surveys["Date"] == d].geometry.union_all() for d in (da, db))
    ta, tb = decimal_year(da), decimal_year(db)
    minx, miny, maxx, maxy = a.union(b).buffer(100).bounds
    size = (int((maxy - miny) / 10), int((maxx - minx) / 10))
    tr = from_bounds(minx, miny, maxx, maxy, size[1], size[0])
    signed = []
    for g in (a, b):
        m = geometry_mask([g], transform=tr, invert=True, out_shape=size)
        signed.append(distance_transform_edt(m) - distance_transform_edt(~m))
    target = (a.area + (t - ta) / (tb - ta) * (b.area - a.area)) / (abs(tr.a) * abs(tr.e))
    lo, hi = 0.0, 1.0
    for _ in range(30):
        w = (lo + hi) / 2
        n = (((1 - w) * signed[0] + w * signed[1]) > 0).sum()
        lo, hi = (w, hi) if (n - target) * (b.area - a.area) < 0 else (lo, w)
    m = ((1 - w) * signed[0] + w * signed[1]) > 0
    g = unary_union([shape(p) for p, v in shapes(m.astype(np.uint8), mask=m, transform=tr) if v == 1])
    print(f"start outline {usgs['date']}: {a.area / 1e6:.2f} km2 ({da}) to {b.area / 1e6:.2f} km2 ({db}), "
          f"weight {w:.2f}, {g.area / 1e6:.2f} km2")
    return g


def cell_size(grid, shape):
    """A grid's cell width and height (m), geographic or projected."""
    if not grid.crs.is_geographic:
        return abs(grid.transform.a), abs(grid.transform.e)
    lat = grid.transform.f + grid.transform.e * shape[0] / 2
    return grid.transform.a * 111320.0 * np.cos(np.radians(lat)), abs(grid.transform.e) * 111320.0


def thickness_on_grid(files, glacier, grid, shape):
    """Millan's thickness sampled once onto a grid, bilinear over his own cells only, with glacier cells he leaves
    bare taking the nearest value and zero off the glacier."""
    ice = np.full(shape, np.nan)
    for path in files:
        with rasterio.open(path) as s:
            out = np.full(shape, np.nan)
            reproject(rasterio.band(s, 1), out, src_transform=s.transform, src_crs=s.crs, src_nodata=0,
                      dst_transform=grid.transform, dst_crs=grid.crs, dst_nodata=np.nan, resampling=Resampling.bilinear)
            ice = np.where(np.isfinite(out) & (out > 0), out, ice)
    thick = np.isfinite(ice)
    if np.any(glacier & ~thick):
        _, (r, k) = distance_transform_edt(~thick, return_indices=True)
        ice[glacier & ~thick] = ice[r, k][glacier & ~thick]
    return np.where(glacier, ice, 0.0)


def rate_on_grid(files, grid, shape):
    """A rate raster mosaic (Hugonnet's dh/dt tiles) sampled once onto a grid, bilinear, with cells it leaves bare
    taking the nearest value."""
    rate = np.full(shape, np.nan)
    for path in files:
        with rasterio.open(path) as s:
            out = np.full(shape, np.nan)
            reproject(rasterio.band(s, 1), out, src_transform=s.transform, src_crs=s.crs, src_nodata=s.nodata,
                      dst_transform=grid.transform, dst_crs=grid.crs, dst_nodata=np.nan, resampling=Resampling.bilinear)
            rate = np.where(np.isfinite(out), out, rate)
    _, (r, k) = distance_transform_edt(~np.isfinite(rate), return_indices=True)
    return rate[r, k]


def surface_and_bed(c, dem, glacier, grid, ice, outlines, surveys, start):
    """The start glacier surface and the bed on one grid (outlines, surveys and the start outline in the UTM CRS).
    The bed is Millan's reference surface (millan_reference: a survey inside his 2010-2020 decade, levelled to the
    DEM by usgs_datum) less his thickness, and that surface itself where the reference outline has no ice, so it does not
    depend on the start. The start surface is the usgs_outline survey (dem), or the surveys it lists (dems)
    interpolated to its date, each levelled to the reference and, with dhdt (a glob of rate tiles), carried to the
    date at that rate. Where later_outline names a later survey, the bed
    under ice lost by then is the ArcticDEM surface after it."""
    usgs, ref, later = c.get("usgs_outline"), c.get("millan_reference"), c.get("later_outline")
    surface, anchor, reference = dem.astype(np.float64), None, None
    if usgs:
        main = outlines.geometry.intersection(start).area.idxmax()
        own = glacier & geometry_mask(list(outlines.loc[[main]].to_crs(grid.crs).geometry), transform=grid.transform,
                                      invert=True, out_shape=dem.shape)
        ever = outlines.copy()  # the survey values cover every cell the glacier held in any of its outlines
        dates = [d for d in usgs.get("outlines", []) + [ref["date"] if ref else None] if d]
        ever.loc[main, "geometry"] = unary_union([start] + [surveys[surveys["Date"] == d].geometry.union_all() for d in dates])
    if ref:
        reference, anchor = survey_surface(dem, own, grid, ever, [os.path.join(HERE, ref["dem"])],
                                           offset=c.get("usgs_datum"))
        in_ref = geometry_mask([surveys[surveys["Date"] == ref["date"]].to_crs(grid.crs).geometry.union_all()],
                               transform=grid.transform, invert=True, out_shape=dem.shape)
    if usgs and (usgs.get("dems") or usgs.get("dem")):
        paths = [os.path.join(HERE, p) for p in usgs.get("dems", [usgs.get("dem")])]
        dhdt = rate_on_grid(sorted(glob.glob(os.path.join(HERE, usgs["dhdt"]))), grid, dem.shape) if usgs.get("dhdt") else None
        surface, _ = survey_surface(dem, glacier, grid, ever, paths, decimal_year(usgs["date"]), anchor=anchor, dhdt=dhdt)
    reference = surface if reference is None else np.where(own, reference, surface)
    bed = np.where(glacier, reference - ice, surface)
    if usgs and later:
        bed = melt_out_bed(dem, surface, bed, glacier, grid, gpd.GeoSeries([start], crs=surveys.crs),
                           surveys[surveys["Date"] == later["date"]].geometry, outlines.geometry,
                           sorted(glob.glob(os.path.join(HERE, later["dems"], "*.tif"))), later.get("reach", 250.0))
    if ref:  # ice-free in the reference year: the bed is its surface (after melt_out_bed, which tapers Millan inward)
        bed = np.where(own & ~in_ref & np.isfinite(reference), reference, bed)
    dx, dy = cell_size(grid, dem.shape)
    above = glacier & (bed > surface)
    ground = np.where(glacier, -np.inf, surface)
    high = np.max([np.roll(ground, s, a) for a in (0, 1) for s in (-1, 1)], axis=0)  # highest ice-free neighbour
    perched = glacier & np.isfinite(high) & (bed > high)
    print(f"bed above the start surface on {above.sum()} glacier cells ({above.sum() * dx * dy / 1e6:.3f} km2, median "
          f"{np.median((bed - surface)[above]) if above.any() else 0:.1f} m), held at the surface; "
          f"{perched.sum()} of {(glacier & np.isfinite(high)).sum()} edge cells have it above their highest ice-free "
          f"neighbour (median {np.median((bed - high)[perched]) if perched.any() else 0:.1f} m), lowered to it")
    bed = np.where(perched, high, bed)  # no bed step up from the ice-free ground at the margin
    return surface, np.maximum(np.minimum(bed, surface), 0)


def melt_out_bed(dem, surface, bed, glacier, src, start, later, outlines, paths, reach=250.0, buffer=1000.0,
                 min_cover=0.5):
    """The bed where the ice melted out between the start and later outlines (GeoSeries) set to the strips' surface,
    and its change carried harmonically over the glacier cells within reach (m) of them, to nothing at the ice-free
    ground and beyond reach. Each strip
    is levelled to the DEM by their median difference on the ground (off all outlines) within buffer (m) of the start
    outline; a cell takes the strips' median where at least min_cover of it is lost ice they cover. The bed is held
    at or below the surface."""
    lost = start.union_all().difference(later.to_crs(start.crs).union_all())
    heights = []
    for path in paths:
        with rasterio.open(path) as s:
            z = s.read(1, masked=True).astype(np.float64).filled(np.nan)
            gone = geometry_mask([gpd.GeoSeries([lost], crs=start.crs).to_crs(s.crs).iloc[0]], transform=s.transform,
                                 invert=True, out_shape=z.shape)
            ice = geometry_mask(list(outlines.to_crs(s.crs).geometry), transform=s.transform, invert=True, out_shape=z.shape)
            near = geometry_mask(list(start.to_crs(s.crs).buffer(buffer)), transform=s.transform, invert=True, out_shape=z.shape)
            means = {}
            for key, values in (("lost", np.where(gone, z, np.nan)), ("ground", np.where(near & ~ice, z, np.nan)),
                                ("cover", (gone & np.isfinite(z)).astype(np.float64))):
                out = np.full(dem.shape, np.nan)
                reproject(values, out, src_transform=s.transform, src_crs=s.crs, src_nodata=np.nan,
                          dst_transform=src.transform, dst_crs=src.crs, dst_nodata=np.nan, resampling=Resampling.average)
                means[key] = out
        offset = np.nanmedian(dem - means["ground"])
        heights.append(np.where(np.nan_to_num(means["cover"]) >= min_cover, means["lost"] + offset, np.nan))
        print(f"{os.path.basename(path)[:8]}: {offset:+.1f} m to the DEM, covers {np.isfinite(heights[-1]).sum()} lost cells")
    with np.errstate(all="ignore"):
        after = np.nanmedian(heights, axis=0) if heights else np.full(dem.shape, np.nan)
    known = glacier & np.isfinite(after)
    dx, dy = cell_size(src, dem.shape)
    near = distance_transform_edt(~known, sampling=(dy, dx)) <= reach
    change = harmonic_fill(np.where(known, np.minimum(after, surface) - bed, 0.0), known, glacier & near)
    moved = glacier & ~known & (np.abs(change) > 1)
    print(f"bed under lost ice on {known.sum()} cells: median change {np.median(change[known]) if known.any() else 0:+.0f} m, "
          f"carried over {moved.sum()} more by over 1 m")
    return np.where(glacier, np.minimum(bed + change, surface), bed)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    p.add_argument("--output-dir", help="write the rasters here instead of the domain's attributes folders")
    a = p.parse_args()
    c = load_config(a.config)
    project, name = c["project_dir"], c["domain"]
    glacier_dir = a.output_dir or os.path.join(project, "attributes", "glaciers")
    dem_dir = os.path.join(project, "attributes", "elevation", "dem")
    bed_dir = a.output_dir or dem_dir
    os.makedirs(glacier_dir, exist_ok=True)

    src = rasterio.open(os.path.join(dem_dir, f"domain_{name}_elv.tif"))
    dem = src.read(1)
    meta = src.meta.copy()
    crs = src.crs
    lat_max, lon_min, lat_min, lon_max = (float(v) for v in c["bounding_box"].split("/"))
    bbox = box(lon_min, lat_min, lon_max, lat_max)
    region = c["rgi6_region"]  # e.g. 01Alaska
    rnum, rname = region[:2], region[2:]

    rgi = gpd.read_file(os.path.join(c["data"]["rgi"], f"nsidc0770_{rnum}.rgi60.{rname}", f"{rnum}_rgi60_{rname}.shp")).to_crs(crs)
    rgi = rgi[rgi.geometry.within(bbox)].copy()
    print(rgi[["RGIId", "Name", "Area", "Zmed"]].to_string(index=False))

    s1 = os.path.join(c["data"]["debris_extent"], "S1", region)
    size = str(c.get("min_glacier_size_km2", 1))
    deb = gpd.read_file(os.path.join(s1, f"{region}_minGl{size}km2_debrisCover.shp")).to_crs(crs)
    abl = gpd.read_file(os.path.join(s1, f"{region}_ablationZone.shp")).to_crs(crs)
    glc = gpd.read_file(os.path.join(s1, f"{region}_minGl1km2.shp")).to_crs(crs)
    deb, abl, glc = (g[g.geometry.within(bbox)].copy() for g in (deb, abl, glc))
    glc["RGIId"] = glc["RGIId"].str.replace("RGI50", "RGI60")  # the outlines are named RGI50 but are RGI 6.0 ids
    for i, glacier in rgi.iterrows():
        if glacier["RGIId"] in glc["RGIId"].values:
            rgi.at[i, "geometry"] = glc[glc["RGIId"] == glacier["RGIId"]]["geometry"].values[0]
    usgs = c.get("usgs_outline")
    if usgs:
        surveys = gpd.read_file(c["data"]["usgs_outlines"]).to_crs(crs)
        surveys = surveys[surveys["Glacier"] == usgs["glacier"]]
        start = start_outline(usgs, surveys.to_crs(c["utm_crs"]))
        u = gpd.GeoSeries([start], crs=c["utm_crs"]).to_crs(crs).iloc[0]
        i = rgi.geometry.intersection(u).area.idxmax()  # the RGI glacier it overlaps most
        print(f"{rgi.at[i, 'RGIId']}: USGS outline of {usgs['date']}")
        rgi.at[i, "geometry"] = u
    deb = gpd.overlay(deb, rgi, how="intersection")
    abl = gpd.overlay(abl, rgi, how="intersection")
    abl = abl.to_crs(c["utm_crs"])
    abl["geometry"] = abl.geometry.buffer(50)  # ablation zones can stop short of the glacier edge
    abl = gpd.overlay(abl.to_crs(crs), glc, how="intersection")

    low = []
    for _, glacier in rgi.iterrows():
        if glacier["RGIId"] not in abl["RGIId_1"].values:  # no ablation zone: Zmed is the equilibrium line
            poly = elevation_polygon(src, glacier.geometry, glacier["Zmed"], "low")
            if poly:
                low.append({**glacier.to_dict(), "geometry": poly})
    if low:
        abl = pd.concat([abl, gpd.GeoDataFrame(low, columns=rgi.columns, crs=crs)], ignore_index=True)
    acc = gpd.overlay(rgi, abl, how="difference")
    deb = gpd.overlay(deb, acc, how="difference")  # no debris in the accumulation zone

    moraine = deb.to_crs(c["utm_crs"])
    for gid in rgi["RGIId"]:
        polys = [g for g in moraine[moraine["RGIId"] == gid].geometry if g.is_valid and not g.is_empty and g.area > 1e4]
        if polys:
            print(f"{gid}: lateral moraine width {np.mean([thinnest_width(g) for g in polys]):.0f} m "
                  f"from {len(polys)} debris polygons")

    def burn(gdf, value, array):
        for geom in gdf.geometry:
            array[geometry_mask([geom], transform=src.transform, invert=True, out_shape=dem.shape)] = value

    dtype = np.full(dem.shape, UPLAND, dtype=np.int16)
    burn(acc, ACCUMULATION, dtype)
    burn(abl, CLEAN_ABLATION, dtype)
    burn(deb, DEBRIS_ABLATION, dtype)
    high = []
    for _, glacier in rgi.iterrows():
        inside = geometry_mask([glacier.geometry], transform=src.transform, invert=True, out_shape=dem.shape)
        if not np.any(dtype[inside] == ACCUMULATION):  # every glacier keeps an accumulation zone
            poly = elevation_polygon(src, glacier.geometry, glacier["Zmax"], "high")
            if poly:
                high.append({**glacier.to_dict(), "geometry": poly})
    if high:
        acc = pd.concat([acc, gpd.GeoDataFrame(high, columns=rgi.columns, crs=crs)], ignore_index=True)
    burn(acc, ACCUMULATION, dtype)
    rgi_id = np.zeros(dem.shape, dtype=np.int32)
    for _, glacier in rgi.iterrows():
        inside = geometry_mask([glacier.geometry], transform=src.transform, invert=True, out_shape=dem.shape)
        rgi_id[inside] = int(glacier["RGIId"][9:]) + int(glacier["RGIId"][6:8]) * 100000
    dtype[rgi_id == 0] = UPLAND  # ablation zones are clipped to the Herreid and Pellicciotti outline, not the final one
    meta.update(count=1, dtype="int16")
    with rasterio.open(os.path.join(glacier_dir, f"domain_{name}_domain_type.tif"), "w", **meta) as dst:
        dst.write(dtype, 1)

    meta.update(count=1, dtype="int32")
    with rasterio.open(os.path.join(glacier_dir, f"domain_{name}_rgi_id.tif"), "w", **meta) as dst:
        dst.write(rgi_id, 1)

    rn = str(int(rnum))
    thick_files = []
    for gid in rgi["RGIId"]:
        for suffix in ("_hdts_m.tif", "_hdts_m_extrap.tif"):  # calibrated, else extrapolated
            path = os.path.join(c["data"]["debris_thickness"], f"region{rn}", f"HMA_DTE_{rn}.{gid[9:]}{suffix}")
            if os.path.exists(path):
                thick_files.append(path)
                break
    debris = np.zeros(dem.shape, dtype=np.float32)
    if thick_files:
        values = mosaic_to_dem(thick_files, crs, dem.shape, src.transform, os.path.join(glacier_dir, "dtk_temp"))
        values[values >= 1.e19] = 0  # no-data fill
        values[values <= c.get("min_debris_thickness", 0.04)] = c.get("min_debris_thickness", 0.04)
        debris[dtype == DEBRIS_ABLATION] = values[dtype == DEBRIS_ABLATION]
    meta.update(count=1, dtype="float32")
    with rasterio.open(os.path.join(glacier_dir, f"domain_{name}_debris_thickness.tif"), "w", **meta) as dst:
        dst.write(debris, 1)

    tdir = os.path.join(c["data"]["ice_thickness"], f"RGI-{rn}")
    ice_files = [os.path.join(tdir, f) for f in sorted(os.listdir(tdir)) if f.startswith(f"THICKNESS_RGI-{rn}.") and f.endswith("tif")]
    rgi_utm = rgi.to_crs(c["utm_crs"])
    surveys_utm = surveys.to_crs(c["utm_crs"]) if usgs else None

    # the DEM grid's surface and bed, for the basin and HRUs; the flow model reads the UTM pair below
    glacier = rgi_id > 0
    print("DEM grid:")
    surface, bed = surface_and_bed(c, dem, glacier, src, thickness_on_grid(ice_files, glacier, src, dem.shape),
                                   rgi_utm, surveys_utm, start if usgs else None)
    for key, values in (("bedrock", bed), ("glacier", surface)):
        with rasterio.open(os.path.join(bed_dir, f"domain_{name}_{key}_elv.tif"), "w", **meta) as dst:
            dst.write(values.astype(np.float32), 1)

    # the same on the UTM grid read_glacier_grids reprojects to, so Millan is sampled once onto the flow grid
    utm = rasterio.crs.CRS.from_string(c["utm_crs"])
    tr, width, height = calculate_default_transform(crs, utm, src.width, src.height, *src.bounds)
    grid = type("Grid", (), {"transform": tr, "crs": utm})
    shape = (height, width)
    dem_u, gid_u = np.full(shape, np.nan), np.zeros(shape, dtype=np.int32)
    reproject(dem.astype(np.float64), dem_u, src_transform=src.transform, src_crs=crs, src_nodata=src.nodata,
              dst_transform=tr, dst_crs=utm, dst_nodata=np.nan, resampling=Resampling.bilinear)
    reproject(rgi_id, gid_u, src_transform=src.transform, src_crs=crs, dst_transform=tr, dst_crs=utm,
              resampling=Resampling.nearest)
    glacier_u = gid_u > 0
    print("UTM grid:")
    surface_u, bed_u = surface_and_bed(c, dem_u, glacier_u, grid, thickness_on_grid(ice_files, glacier_u, grid, shape),
                                       rgi_utm, surveys_utm, start if usgs else None)
    meta_u = {**meta, "crs": utm, "transform": tr, "width": width, "height": height, "dtype": "float32"}
    for key, values in (("bedrock", bed_u), ("glacier", surface_u)):
        with rasterio.open(os.path.join(bed_dir, f"domain_{name}_{key}_elv_utm.tif"), "w", **meta_u) as dst:
            dst.write(values.astype(np.float32), 1)
    src.close()
    print(f"wrote the domain type, RGI id and debris rasters to {glacier_dir} and the bed to {bed_dir}")


if __name__ == "__main__":
    main()
