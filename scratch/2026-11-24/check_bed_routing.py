#!/usr/bin/env python3
"""How much glacier_extend.py's depression fill raises each domain's geographic bed DEM: at the snapped gauge, over the basin and over
the advance-room cells (rgi_id_extend beyond the start outline); and the raw pysheds catchment against the saved basin.

    check_bed_routing.py
"""
import glob
import os
import sys

import geopandas as gpd
import numpy as np
import rasterio
import rasterio.features

WF = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, WF)
from domain_config import load_config  # noqa: E402
from glacier_extend import delineate  # noqa: E402

for yaml in ["wolverine", "wolverine_general", "gulkana", "gulkana_general", "lemon_creek", "lemon_creek_general"]:
    c = load_config(os.path.join(WF, "domains", f"{yaml}.yaml"))
    project, name = c["project_dir"], c["domain"]
    bed = os.path.join(project, "attributes", "elevation", "dem", f"domain_{name}_bedrock_elv.tif")
    lat, lon = (float(v) for v in c["pour_point"].split("/"))
    grid, dem, fdir, acc, catch = delineate(bed, lat, lon)
    filled = np.asarray(grid.fill_depressions(grid.fill_pits(dem)))
    raise_m = filled - np.asarray(dem)
    catch = np.asarray(catch).astype(bool)
    basin = gpd.read_file(glob.glob(os.path.join(project, "shapefiles", "river_basins", "*.shp"))[0]).to_crs(grid.crs)
    bmask = rasterio.features.geometry_mask(list(basin.geometry), dem.shape, grid.affine, invert=True)
    with rasterio.open(os.path.join(project, "attributes", "glaciers", f"domain_{name}_rgi_id.tif")) as r:
        start = r.read(1) > 0
    with rasterio.open(os.path.join(project, "attributes", "glaciers", f"domain_{name}_rgi_id_extend.tif")) as r:
        room = (r.read(1) > 0) & ~start
    x, y = grid.snap_to_mask(acc > 1000, (lon, lat))
    col, row = ~grid.affine * (x, y)
    gi, gj = int(row), int(col)
    a = np.asarray(dem)
    print(f"{yaml:20s} edge min {min(a[0].min(), a[-1].min(), a[:, 0].min(), a[:, -1].min()):6.0f}  dem min {a.min():6.0f}  "
          f"fill at gauge {raise_m[gi, gj]:5.1f} m  basin cells raised >1 m {100 * np.mean(raise_m[bmask] > 1):4.1f}% (max {raise_m[bmask].max():5.1f})  "
          f"room cells raised >1 m {100 * np.mean(raise_m[room] > 1) if room.any() else 0:4.1f}% of {room.sum()}  "
          f"catchment {catch.sum()} cells, saved basin {bmask.sum()}, overlap {(catch & bmask).sum()}")
