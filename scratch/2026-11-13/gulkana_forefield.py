#!/usr/bin/env python3
"""Gulkana's forefield from Sentinel-2: the braidplain's gravel extent and its wetted area on every clear summer scene,
against the gauge's flow that day.

Gravel: outside the USGS glacier outline, sloping under SLOPE_MAX on the USGS 2016 survey DEM (2 m, averaged to the
10 m Sentinel grid), and unvegetated (median NDVI of the clear scenes under NDVI_MAX); the largest connected patch
is the braidplain. Wetted area: in each scene, the water fraction of each gravel pixel unmixed from 1.6 um SWIR between
dry gravel (that scene's 90th percentile in the plain) and turbid water (SWIR_WATER), so threads narrower than a pixel
count. Turbid glacial water still absorbs at 1.6 um, where NDWI-type tests read it as gravel.

    ./gulkana_forefield.py OUT_DIR [--first 2017-06-01] [--last 2026-09-30]
      writes OUT_DIR/gulkana_forefield.csv (date, scene, wetted_km2, gravel_km2, bad, snow, q_cms) and
      OUT_DIR/gulkana_forefield.png (the gravel outline and the wetted fraction at the lowest and highest flows)
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
from rasterio.features import rasterize
from rasterio.warp import Resampling, reproject
from rasterio.windows import from_bounds
from pyproj import Transformer
from scipy import ndimage

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from acquire_lake_area import SCL_BAD, SCL_SNOW, SOURCES, search  # noqa: E402
from acquire_streamflow import fetch_usgs  # noqa: E402

BOX = (-145.4731, 63.2381, -145.4210, 63.2609)   # terminus to gauge, 250 m beyond (domains/gulkana.yaml)
EXT = os.path.join(HERE, "..", "..", "data", "external", "GlacierDEM")
DEM = os.path.join(EXT, "Deltas_20160830_DEM", "Deltas_20160830_DEM.tif")
OUTLINES = os.path.join(EXT, "USGS_Glacier_Boundaries_shp", "USGS_Glacier_Boundaries.shp")
SITE = "15478040"
SLOPE_MAX, NDVI_MAX, SWIR_WATER = 4.0, 0.2, 0.03


def grid(item):
    """The scene's 10 m grid over the box: transform, shape and CRS of its green band window."""
    with rasterio.open(item["assets"]["green"]["href"]) as r:
        T = Transformer.from_crs(4326, r.crs, always_xy=True)
        (x0, x1), (y0, y1) = zip(T.transform(BOX[0], BOX[1]), T.transform(BOX[2], BOX[3]))
        w = from_bounds(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), r.transform).round_offsets().round_lengths()
        return r.window_transform(w), (int(w.height), int(w.width)), r.crs, w


def band(item, key, shape, h):
    """One band over the box on the scene's 10 m grid, as reflectance."""
    a = item["assets"][key]
    _, _, crs, w10 = GRID
    with rasterio.open(a["href"]) as r:
        scale = 10.0 / r.res[0]
        win = rasterio.windows.Window(w10.col_off * scale, w10.row_off * scale, w10.width * scale, w10.height * scale)
        x = r.read(1, window=win, out_shape=shape, boundless=True, resampling=Resampling.bilinear if key != "scl" else Resampling.nearest)
    if key == "scl":
        return x
    rb = (a.get("raster:bands") or [{}])[0]
    return x * rb.get("scale", 1.0) + (0.0 if h else rb.get("offset", 0.0))


def static_layers(transform, shape, crs, year):
    """Slope (deg) from the 2016 DEM and the glacier mask from the USGS outline nearest the year, on the 10 m grid."""
    z = np.full(shape, np.nan, np.float32)
    with rasterio.open(DEM) as r:
        reproject(rasterio.band(r, 1), z, dst_transform=transform, dst_crs=crs, resampling=Resampling.average,
                  dst_nodata=np.nan)
    gy, gx = np.gradient(ndimage.uniform_filter(np.nan_to_num(z, nan=np.nanmean(z)), 3), 10.0)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    o = gpd.read_file(OUTLINES)
    o = o[o.Glacier.str.contains("Gulkana")]
    o = o[o.Year == o.Year.iloc[(o.Year - year).abs().argsort().iloc[0]]].to_crs(crs)
    ice = rasterize(o.geometry, out_shape=shape, transform=transform, fill=0, default_value=1).astype(bool)
    return slope, ndimage.binary_dilation(ice, iterations=2)


def main():
    global GRID
    p = argparse.ArgumentParser()
    p.add_argument("out_dir")
    p.add_argument("--first", default="2017-06-01")
    p.add_argument("--last", default="2026-09-30")
    a = p.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    src = SOURCES["sentinel2"]
    items = [i for i in search(src, BOX, a.first, a.last, 60) if int(i["properties"]["datetime"][5:7]) in (6, 7, 8, 9)]
    q = fetch_usgs(SITE, a.first, a.last)
    scenes = []
    for it in items:
        try:
            GRID = grid(it)
        except Exception:
            continue
        h = bool(it["properties"].get("earthsearch:boa_offset_applied"))
        shape = GRID[1]
        scl = band(it, "scl", shape, h)
        bad, snow = np.isin(scl, SCL_BAD).mean(), np.isin(scl, SCL_SNOW).mean()
        if bad > 0.05 or snow > 0.3:
            continue
        R, N, W = band(it, "red", shape, h), band(it, "nir", shape, h), band(it, "swir16", shape, h)
        scenes.append((it, R, N, W, bad, snow))
        print(it["id"], f"bad {bad:.2f} snow {snow:.2f}", flush=True)
    # one grid for all: the scenes share the tile grid; keep those that match the first
    shape0 = scenes[0][1].shape
    scenes = [s for s in scenes if s[1].shape == shape0]
    GRID = grid(scenes[0][0])
    transform, shape, crs, _ = GRID
    slope, ice = static_layers(transform, shape, crs, 2016)
    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = np.nanmedian(np.stack([(N - R) / (N + R) for _, R, N, _, _, _ in scenes]), axis=0)
    flat = (slope < SLOPE_MAX) & (ndvi < NDVI_MAX) & ~ice
    lab, n = ndimage.label(ndimage.binary_opening(flat, iterations=1))
    plain = lab == (np.argmax(np.bincount(lab.ravel())[1:]) + 1) if n else flat
    plain = ndimage.binary_closing(plain, iterations=2) & ~ice
    gravel_km2 = plain.sum() * 100 / 1e6
    rows, fracs = [], {}
    for it, R, N, W, bad, snow in scenes:
        day = it["properties"]["datetime"][:10]
        dry = np.nanpercentile(W[plain], 90)
        f = np.clip((dry - W) / (dry - SWIR_WATER), 0, 1) * plain
        wet = float(np.nansum(f)) * 100 / 1e6
        qq = q.get(datetime.date.fromisoformat(day), np.nan)
        rows.append([day, it["id"], f"{wet:.4f}", f"{gravel_km2:.4f}", f"{bad:.3f}", f"{snow:.3f}", qq])
        fracs[day] = (f, qq)
    with open(os.path.join(a.out_dir, "gulkana_forefield.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "scene", "wetted_km2", "gravel_km2", "bad", "snow", "q_cms"])
        w.writerows(rows)
    qs = {d: v[1] for d, v in fracs.items() if np.isfinite(v[1])}
    lo, hi = min(qs, key=qs.get), max(qs, key=qs.get)
    fig, ax = plt.subplots(1, 3, figsize=(15, 5))
    ax[0].imshow(ndvi, cmap="BrBG", vmin=-0.2, vmax=0.6); ax[0].contour(plain, [0.5], colors="r", linewidths=0.8)
    ax[0].contour(ice, [0.5], colors="c", linewidths=0.8)
    ax[0].set_title(f"braidplain {gravel_km2:.3f} km2 (red), glacier (cyan), NDVI", fontsize=9)
    for x, d in zip(ax[1:], (lo, hi)):
        x.imshow(fracs[d][0], cmap="Blues", vmin=0, vmax=1)
        x.set_title(f"{d}: {qs[d]:.1f} m3/s, wetted {np.nansum(fracs[d][0]) * 100 / 1e6:.3f} km2", fontsize=9)
    for x in ax:
        x.set_xticks([]); x.set_yticks([])
    fig.tight_layout(); fig.savefig(os.path.join(a.out_dir, "gulkana_forefield.png"), dpi=110)
    print("wrote", a.out_dir)


if __name__ == "__main__":
    main()
