#!/usr/bin/env python3
"""Wolverine lake level and depth: the water surface in each ArcticDEM strip over the lake box (the flat lowest
pixels), against the bed DEM there, and the lake's mean depth when the bed is filled to that level over the
imagery's area.

    ./lake_depth.py [WORKFLOW_DIR]
"""
import glob
import os
import sys

import numpy as np
import rasterio
from rasterio.warp import transform as warp_xy, transform_bounds

W = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
D = os.path.join(W, "data")
BOX = [-148.918, 60.3720, -148.905, 60.3775]
bed_tif = os.path.join(D, "domain_Wolverine", "attributes", "elevation", "dem", "domain_Wolverine_bedrock_elv_utm.tif")
with rasterio.open(bed_tif) as r:
    l, b, rr, t = transform_bounds("EPSG:4326", r.crs, *BOX)
    win = rasterio.windows.from_bounds(l, b, rr, t, r.transform).round_offsets().round_lengths()
    bed = r.read(1, window=win, masked=True).astype(float).filled(np.nan)
    btr, bcrs = r.window_transform(win), r.crs
cell = abs(btr.a * btr.e)
ok = np.isfinite(bed)
print(f"bed DEM box: {ok.sum()} cells of {np.sqrt(cell):.0f} m, bed {np.nanmin(bed):.1f}-{np.nanmax(bed):.1f} m")

print("\nstrip                 lowest 1%   5%    10%  (m, lake-box pixels)")
levels = []
for f in sorted(glob.glob(os.path.join(D, "external", "GlacierDEM", "ArcticDEM_Wolverine_series", "*.tif"))):
    with rasterio.open(f) as r:
        try:
            w = rasterio.windows.from_bounds(*transform_bounds("EPSG:4326", r.crs, *BOX), r.transform).round_offsets().round_lengths()
            z = r.read(1, window=w, masked=True, boundless=True).astype(float).filled(np.nan)
        except Exception:
            continue
    z = z[np.isfinite(z) & (z > 0)]
    if z.size < 1000:
        continue
    p = np.percentile(z, [1, 5, 10])
    levels.append((os.path.basename(f)[:8], p[0]))
    print(f"{os.path.basename(f)[:8]}  {z.size:8d} px  {p[0]:7.1f} {p[1]:7.1f} {p[2]:7.1f}")

print("\nbed filled to a level: area and mean depth over the box's bed cells")
for level in np.arange(np.floor(np.nanmin(bed)), np.nanmin(bed) + 30, 2.0):
    wet = ok & (bed < level)
    if wet.any():
        print(f"  level {level:6.1f} m  area {wet.sum()*cell:8.0f} m2  mean depth {np.mean(level - bed[wet]):5.2f} m  max {np.max(level - bed[wet]):5.2f} m")

# stage-area power: depth below the level against the area wetted, A ~ h**(1/s) -> fit log h on log A
for amax in (35000, 37000, 57000):
    order = np.sort(bed[ok])
    n = int(round(amax / cell))
    if n < 3:
        continue
    level = order[n - 1]
    a = np.arange(1, n + 1) * cell
    h = order[:n] - order[0]
    k = h > 0
    s = np.polyfit(np.log(a[k]), np.log(h[k]), 1)[0]
    print(f"\nlake of {amax} m2 in the lowest bed cells: level {level:.1f} m, mean depth {np.mean(level - order[:n]):.2f} m, "
          f"max {level - order[0]:.2f} m, stage ~ area**{s:.2f} (wetlandShape)")
