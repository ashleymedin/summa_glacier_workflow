#!/usr/bin/env python3
"""Fetch the ArcticDEM strips (Polar Geospatial Center, 2 m s2s041 release) over a glacier dated after its later
outline, July to October, for glacier_rasters.py's bed where the ice melted out.

The domain YAML's later_outline names the outline (a USGS survey date of the usgs_outline glacier) and the folder
the strips go to (dems). Each strip is read at its 8 m overview, clipped to the starting outline buffered by
--buffer, and written there as <date>_<strip id>.tif in its own CRS (EPSG:3413, WGS84 ellipsoid heights, NaN
no-data), with the cells the strip's bitmask flags (edge, water, cloud) left out. Strips covering less than --min-cover of the clip are skipped.

    ./acquire_arcticdem.py domains/gulkana.yaml
"""

import argparse
import os

import certifi
import geopandas as gpd
import numpy as np
import pystac_client
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window, from_bounds

from domain_config import load_config

HERE = os.path.dirname(os.path.abspath(__file__))
STAC = "https://stac.pgc.umn.edu/api/v1"
COLLECTION = "arcticdem-strips-s2s041-2m"
os.environ.setdefault("CURL_CA_BUNDLE", certifi.where())
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")


def read_clip(href, bounds, step, resampling=Resampling.average):
    """The strip over bounds (its CRS) at step times its resolution, NaN off the strip, and that grid's transform."""
    with rasterio.open(href) as s:
        w = from_bounds(*bounds, s.transform).round_offsets().round_lengths()
        r0, c0, h, wd = int(w.row_off), int(w.col_off), int(w.height) // step, int(w.width) // step
        ri, ci = r0 + -(-max(-r0, 0) // step) * step, c0 + -(-max(-c0, 0) // step) * step  # on the clip's coarse grid
        r1, c1 = r0 + min(h, (s.height - r0) // step) * step, c0 + min(wd, (s.width - c0) // step) * step
        z = np.full((h, wd), np.nan, dtype=np.float32)
        if r1 > ri and c1 > ci:
            a = s.read(1, window=Window(ci, ri, c1 - ci, r1 - ri), out_shape=((r1 - ri) // step, (c1 - ci) // step),
                       resampling=resampling, masked=True).astype(np.float32).filled(np.nan)
            z[(ri - r0) // step:(r1 - r0) // step, (ci - c0) // step:(c1 - c0) // step] = a
        t = s.window_transform(Window(c0, r0, wd * step, h * step)) * rasterio.Affine.scale(step)
        return z, t, s.crs


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    p.add_argument("--buffer", type=float, default=1000.0, help="m around the starting outline, for stable ground")
    p.add_argument("--min-cover", type=float, default=0.3, help="least valid share of the clip a strip keeps")
    p.add_argument("--step", type=int, default=4, help="strip pixels per output pixel (4: the 8 m overview)")
    a = p.parse_args()
    c = load_config(a.config)
    later, usgs = c["later_outline"], c["usgs_outline"]
    out_dir = os.path.join(HERE, later["dems"])
    os.makedirs(out_dir, exist_ok=True)

    u = gpd.read_file(c["data"]["usgs_outlines"])
    start = u[(u["Glacier"] == usgs["glacier"]) & (u["Date"] == usgs["date"])].to_crs(c["utm_crs"])
    area = start.buffer(a.buffer).to_crs(3413).union_all()
    date = later["date"].replace("/", "-")
    footprint = gpd.GeoSeries([area], crs=3413).to_crs(4326).iloc[0]
    items = pystac_client.Client.open(STAC).search(collections=[COLLECTION], intersects=footprint,
                                                   datetime=f"{date}T00:00:00Z/..").item_collection()
    items = [i for i in items if 7 <= i.datetime.month <= 10]
    print(f"{len(items)} {COLLECTION} strips from July to October after {date}")
    bounds = tuple(8 * round(b / 8) for b in area.bounds)
    for it in sorted(items, key=lambda i: i.datetime):
        z, t, crs = read_clip(it.assets["dem"].href, bounds, a.step)
        bits, _, _ = read_clip(it.assets["mask"].href, bounds, a.step, Resampling.nearest)
        z[bits != 0] = np.nan  # edge, water or cloud
        cover = np.isfinite(z).mean()
        if cover < a.min_cover:
            print(f"  {it.id}: covers {cover:.0%}, skipped")
            continue
        path = os.path.join(out_dir, f"{it.datetime:%Y%m%d}_{it.id}.tif")
        with rasterio.open(path, "w", driver="GTiff", height=z.shape[0], width=z.shape[1], count=1, dtype="float32",
                           crs=crs, transform=t, nodata=np.nan, compress="deflate") as dst:
            dst.write(z, 1)
        print(f"  {os.path.basename(path)}: covers {cover:.0%}")


if __name__ == "__main__":
    main()
