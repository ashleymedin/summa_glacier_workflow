#!/usr/bin/env python3
"""A glacier forefield's braidplain and its wetted area on every clear summer Sentinel-2 scene, against the gauge's flow.

Plain: sloping under SLOPE_MAX on the site's USGS survey DEM (averaged to the 10 m grid), unvegetated (median NDVI of the
clear scenes under NDVI_MAX), and outside the latest USGS glacier outline: the largest connected patch of that ground.
Each scene counts the part outside the outline of the year nearest it, and the older outlines show how much of the
plain was still under ice. Wetted area: the water fraction of each plain
pixel unmixed from 1.6 um SWIR between dry gravel (the scene's 90th percentile in the plain) and turbid water
(SWIR_WATER), so threads narrower than a pixel count; turbid glacial water absorbs at 1.6 um where NDWI-type tests read
it as gravel. Where the site has a lake, pixels passing the lake's open-water test (acquire_lake_area.py) are the lake's,
counted apart from the braided area.

    ./forefield_wetted.py SITE OUT_DIR [--first 2017-06-01] [--last 2026-09-30]
      SITE gulkana or wolverine; writes OUT_DIR/SITE_forefield.csv (date, scene, wetted_km2, lake_km2, plain_km2, bad,
      snow, q_cms), OUT_DIR/SITE_forefield.npz (the plain and the outlines' masks) and OUT_DIR/SITE_forefield.png
"""
import argparse
import csv
import datetime
import os
import sys

import geopandas as gpd
import matplotlib
import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.features import rasterize
from rasterio.warp import Resampling, reproject
from rasterio.windows import Window, from_bounds
from scipy import ndimage

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from acquire_lake_area import SCL_BAD, SCL_SNOW, SOURCES, search  # noqa: E402
from acquire_streamflow import fetch_usgs  # noqa: E402

EXT = os.path.join(HERE, "..", "..", "data", "external", "GlacierDEM")
SITES = {   # terminus-to-gauge boxes of domains/*.yaml lake_area
    "gulkana": dict(box=(-145.4731, 63.2381, -145.4210, 63.2609), site="15478040", glacier="Gulkana",
                    dem="Deltas_20160830_DEM/Deltas_20160830_DEM.tif", lake=False),
    "wolverine": dict(box=(-148.9215, 60.3684, -148.8922, 60.3828), site="15236900", glacier="Wolverine",
                      dem="EasternKenai_20150813_DEM/EasternKenai_20150813_DEM.tif", lake=True),
}
OUTLINES = os.path.join(EXT, "USGS_Glacier_Boundaries_shp", "USGS_Glacier_Boundaries.shp")
SLOPE_MAX, NDVI_MAX, SWIR_WATER = 4.0, 0.2, 0.03
LAKE_TEST = (0.3, 0.6, 0.25)   # NDWI, MNDWI above; blue below (acquire_lake_area.py defaults)


def window(item, box):
    with rasterio.open(item["assets"]["green"]["href"]) as r:
        T = Transformer.from_crs(4326, r.crs, always_xy=True)
        (x0, x1), (y0, y1) = zip(T.transform(box[0], box[1]), T.transform(box[2], box[3]))
        w = from_bounds(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), r.transform).round_offsets().round_lengths()
        return r.window_transform(w), (int(w.height), int(w.width)), r.crs, w


def band(item, key, grid, h):
    a = item["assets"][key]
    _, shape, _, w10 = grid
    with rasterio.open(a["href"]) as r:
        s = 10.0 / r.res[0]
        win = Window(w10.col_off * s, w10.row_off * s, w10.width * s, w10.height * s)
        x = r.read(1, window=win, out_shape=shape, boundless=True,
                   resampling=Resampling.nearest if key == "scl" else Resampling.bilinear)
    if key == "scl":
        return x
    rb = (a.get("raster:bands") or [{}])[0]
    return x * rb.get("scale", 1.0) + (0.0 if h else rb.get("offset", 0.0))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("site", choices=SITES)
    p.add_argument("out_dir")
    p.add_argument("--first", default="2017-06-01")
    p.add_argument("--last", default="2026-09-30")
    a = p.parse_args()
    cfg = SITES[a.site]
    os.makedirs(a.out_dir, exist_ok=True)
    src = SOURCES["sentinel2"]
    items = [i for i in search(src, cfg["box"], a.first, a.last, 60) if int(i["properties"]["datetime"][5:7]) in (6, 7, 8, 9)]
    q = fetch_usgs(cfg["site"], a.first, a.last)
    grid, scenes = None, []
    for it in items:
        try:
            g = window(it, cfg["box"])
        except Exception:
            continue
        if grid is None:
            grid = g
        if g[1] != grid[1] or g[2] != grid[2]:
            continue
        h = bool(it["properties"].get("earthsearch:boa_offset_applied"))
        scl = band(it, "scl", grid, h)
        bad, snow = np.isin(scl, SCL_BAD).mean(), np.isin(scl, SCL_SNOW).mean()
        if bad > 0.05 or snow > 0.3:
            continue
        bands = {k: band(it, k, grid, h) for k in ("blue", "green", "red", "nir", "swir16")}
        scenes.append((it, bands, bad, snow))
        print(it["id"], f"bad {bad:.2f} snow {snow:.2f}", flush=True)
    transform, shape, crs, _ = grid
    z = np.full(shape, np.nan, np.float32)
    with rasterio.open(os.path.join(EXT, cfg["dem"])) as r:
        reproject(rasterio.band(r, 1), z, dst_transform=transform, dst_crs=crs, resampling=Resampling.average, dst_nodata=np.nan)
    gy, gx = np.gradient(ndimage.uniform_filter(np.nan_to_num(z, nan=np.nanmean(z)), 3), 10.0)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    o = gpd.read_file(OUTLINES)
    o = o[o.Glacier.str.contains(cfg["glacier"])].to_crs(crs)
    ice = {int(y): ndimage.binary_dilation(rasterize(o[o.Year == y].geometry, out_shape=shape, transform=transform,
                                                     fill=0, default_value=1).astype(bool), iterations=2)
           for y in sorted(o.Year.unique())}
    years = np.array(sorted(ice))
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = np.nanmedian(np.stack([(b["nir"] - b["red"]) / (b["nir"] + b["red"]) for _, b, _, _ in scenes]), axis=0)
    flat = (slope < SLOPE_MAX) & (ndvi < NDVI_MAX) & ~ice[int(years[-1])]
    lab, n = ndimage.label(ndimage.binary_opening(flat, iterations=1))
    plain = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1) if n else flat
    plain = ndimage.binary_closing(plain, iterations=2)
    rows, fracs = [], {}
    for it, b, bad, snow in scenes:
        day = it["properties"]["datetime"][:10]
        free = plain & ~ice[int(years[np.abs(years - int(day[:4])).argmin()])]
        lake = np.zeros(shape, bool)
        if cfg["lake"]:
            with np.errstate(divide="ignore", invalid="ignore"):
                lake = (((b["green"] - b["nir"]) / (b["green"] + b["nir"]) > LAKE_TEST[0])
                        & ((b["green"] - b["swir16"]) / (b["green"] + b["swir16"]) > LAKE_TEST[1]) & (b["blue"] < LAKE_TEST[2]))
            lake = ndimage.binary_opening(lake, iterations=1)
        dry = np.nanpercentile(b["swir16"][free & ~lake], 90)
        f = np.clip((dry - b["swir16"]) / (dry - SWIR_WATER), 0, 1) * (free & ~lake)
        qq = q.get(datetime.date.fromisoformat(day), np.nan)
        rows.append([day, it["id"], f"{np.nansum(f) * 100 / 1e6:.4f}", f"{(lake & free).sum() * 100 / 1e6:.4f}",
                     f"{free.sum() * 100 / 1e6:.4f}", f"{bad:.3f}", f"{snow:.3f}", qq])
        fracs[day] = (f, lake & free, qq)
    stem = os.path.join(a.out_dir, f"{a.site}_forefield")
    with open(stem + ".csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "scene", "wetted_km2", "lake_km2", "plain_km2", "bad", "snow", "q_cms"])
        w.writerows(rows)
    np.savez_compressed(stem + ".npz", plain=plain, ndvi=ndvi, slope=slope, years=years,
                        **{f"ice{y}": ice[y] for y in years}, transform=np.array(transform)[:6], crs=str(crs))
    qs = {d: v[2] for d, v in fracs.items() if np.isfinite(v[2])}
    lo, hi = min(qs, key=qs.get), max(qs, key=qs.get)
    fig, ax = plt.subplots(1, 3, figsize=(15, 5))
    ax[0].imshow(ndvi, cmap="BrBG", vmin=-0.2, vmax=0.6)
    ax[0].contour(plain, [0.5], colors="r", linewidths=0.8)
    for y, c in ((years[0], "c"), (years[-1], "b")):
        ax[0].contour(ice[y], [0.5], colors=c, linewidths=0.8)
    ax[0].set_title(f"plain (red), glacier {years[0]} (cyan) and {years[-1]} (blue), NDVI", fontsize=9)
    for x, d in zip(ax[1:], (lo, hi)):
        x.imshow(fracs[d][0], cmap="Blues", vmin=0, vmax=1)
        if cfg["lake"]:
            x.contour(fracs[d][1], [0.5], colors="m", linewidths=0.8)
        x.set_title(f"{d}: {qs[d]:.1f} m3/s, braided {np.nansum(fracs[d][0]) * 100 / 1e6:.3f} km2"
                    + (f", lake (magenta) {fracs[d][1].sum() * 100 / 1e6:.3f}" if cfg["lake"] else ""), fontsize=9)
    for x in ax:
        x.set_xticks([]); x.set_yticks([])
    fig.tight_layout(); fig.savefig(stem + ".png", dpi=110)
    print("wrote", stem)


if __name__ == "__main__":
    main()
