#!/usr/bin/env python3
"""Delineate a glacier basin on its bed and give each glacier room to advance downstream.

A glacier surface is convex, so the basin is delineated with pysheds on the bed DEM (glacier_rasters.py),
lumped above the gauge. Writes shapefiles/river_basins/<name>_riverBasins_lumped.shp and, in
attributes/glaciers, the glacier-capable versions of the type and RGI id rasters:

  domain_<name>_domain_type_extend.tif   glaciers less than --gru-threshold inside the basin made upland
  domain_<name>_rgi_id_extend.tif        each glacier's id extended over the cells it may advance into

Extension, largest glacier first, by --method:
  drag  the terminus (the glacier's highest-accumulation cells) is shifted cell by cell down the flow
        direction until it has added (glacier cells)^(2/3) cells or meets the basin edge or another glacier
  fill  from the terminus, cells downstream and around it are flooded while their height above nearest
        drainage is below the terminus ice thickness (at least 50 m), to the same cell count

    ./glacier_extend.py domains/wolverine.yaml
"""

import argparse
import os
import sys

import geopandas as gpd
import numpy as np
import rasterio
import rasterio.features
from pysheds.grid import Grid
from shapely.geometry import Polygon

from domain_config import load_config

SURROUND = {0: (0, -1), 1: (1, -1), 2: (1, 0), 3: (1, 1), 4: (0, 1), 5: (-1, 1), 6: (-1, 0), 7: (-1, -1)}
NEXT_CELL = {64: (0, -1), 128: (1, -1), 1: (1, 0), 2: (1, 1), 4: (0, 1), 8: (-1, 1), 16: (-1, 0), 32: (-1, -1)}


def delineate(bed_path, pour_lat, pour_lon, snap_threshold=1000):
    """Lumped basin above the pour point on the bed DEM: grid, flow direction, accumulation, basin mask."""
    grid = Grid.from_raster(bed_path)
    dem = grid.read_raster(bed_path)
    conditioned = grid.resolve_flats(grid.fill_depressions(grid.fill_pits(dem)))
    fdir = grid.flowdir(conditioned)
    acc = grid.accumulation(fdir)
    x, y = grid.snap_to_mask(acc > snap_threshold, (pour_lon, pour_lat))
    catch = grid.catchment(x=x, y=y, fdir=fdir, xytype="coordinate")
    return grid, dem, fdir, acc, catch


def terminus_shapes(grid, fdir, acc, gid, glacier_id):
    """The glacier's terminus cell and a small terminus piece: the glacier cells draining to the terminus less
    those draining to a cell a little upstream of it."""
    acc_glacier = acc.copy()
    acc_glacier[gid != glacier_id] = 0
    y, x = np.where(acc_glacier >= np.percentile(acc_glacier[acc_glacier > 0], 100))
    gridyx = (y[0], x[0])

    def upstream(yx):
        shape = np.where(grid.catchment(x=yx[1], y=yx[0], fdir=fdir, xytype="index"), 1, 0).astype(np.uint8)
        shape[gid != glacier_id] = 0
        return shape

    shape0 = upstream(gridyx)
    percentile, y1, x1, n = 100, y, x, 0
    shape1 = shape0.copy()
    while (y1[n] == y[0] and x1[n] == x[0]) or (shape0 - shape1).sum() < 2:
        percentile -= 0.1
        y1, x1 = np.where(acc_glacier >= np.percentile(acc_glacier[acc_glacier > 0], percentile))
        n = acc_glacier[y1, x1].argmin()  # the most upstream of them
        gridyx = (y1[n], x1[n])
        shape1 = upstream(gridyx)
    return acc_glacier, gridyx, shape0, shape1


def drag(grid, fdir, acc, gid, glacier_id, possible):
    """Cells the glacier may advance into by dragging its terminus downstream."""
    acc_glacier, gridyx, shape0, shape1 = terminus_shapes(grid, fdir, acc, gid, glacier_id)
    ext_shape = shape0 - shape1
    y, x = np.where(ext_shape == 1)
    for i in range(x.size):  # thicken a terminus one cell thick to two
        if np.sum(ext_shape[y[i] - 1:y[i] + 2, x[i] - 1:x[i] + 2]) <= 4:
            for dx, dy in SURROUND.values():
                nx_, ny_ = x[i] + dx, y[i] + dy
                if 0 <= ny_ < ext_shape.shape[0] and 0 <= nx_ < ext_shape.shape[1] and shape0[ny_, nx_] == 1:
                    ext_shape[ny_, nx_] = 1
    size = ext_shape.sum()
    ncell = int(acc_glacier[acc_glacier > 0].size ** (2. / 3.))
    extend = ext_shape
    added = 0
    cellxy = (gridyx[1], gridyx[0])
    possible0 = possible.copy()
    possible0[gid == glacier_id] = 1  # it may also spread beside itself
    while added < ncell:
        step = NEXT_CELL[fdir[cellxy[1], cellxy[0]]]
        new_x, new_y = cellxy[0] + step[0], cellxy[1] + step[1]
        if not (0 <= new_y < possible.shape[0] and 0 <= new_x < possible.shape[1]) or possible0[new_y, new_x] != 1:
            break
        new_shape = np.zeros_like(ext_shape)
        y, x = np.where(ext_shape == 1)
        for i in range(x.size):
            x0, y0 = x[i] + step[0], y[i] + step[1]
            if 0 <= y0 < possible.shape[0] and 0 <= x0 < possible.shape[1]:
                new_shape[y0, x0] = 1
        extend[new_shape == 1] = 1
        added += new_shape[possible == 1].sum()  # only cells not already glacier
        possible[extend == 1] = 0
        ext_shape = new_shape
        cellxy = (new_x, new_y)
    y, x = np.where(extend == 0)
    for i in range(x.size):  # fill one-cell holes
        if 0 < y[i] < extend.shape[0] - 1 and 0 < x[i] < extend.shape[1] - 1:
            if np.sum(extend[y[i] - 1:y[i] + 2, x[i] - 1:x[i] + 2]) == 8 and possible[y[i], x[i]] == 1:
                extend[y[i], x[i]] = 1
                added += 1
    print(f"glacier {glacier_id} extended by {added} cells with a terminus of {size}, {ncell} cells requested")
    return extend


def inundate(dem_surf, dem, origxy, gid, glacier_id, cellxy, possible, hand, height, extend, ncell, added):
    """Flood the cells around a cell that are glacier-capable, low enough above drainage and below the terminus."""
    for dx, dy in SURROUND.values():
        new_x, new_y = cellxy[0] + dx, cellxy[1] + dy
        if 0 <= new_y < possible.shape[0] and 0 <= new_x < possible.shape[1]:
            if (possible[new_y, new_x] == 1 and hand[new_y, new_x] < height and extend[new_y, new_x] == 0
                    and dem[new_y, new_x] <= dem_surf[origxy[1], origxy[0]]):
                extend[new_y, new_x] = 1
                if gid[new_y, new_x] != glacier_id:
                    added += 1
                if added >= ncell:
                    return extend, added
                extend, added = inundate(dem_surf, dem, origxy, gid, glacier_id, (new_x, new_y), possible,
                                         hand, height, extend, ncell, added)
                if added >= ncell:
                    return extend, added
    return extend, added


def fill(grid, dem, dem_surf, fdir, acc, hand, gid, glacier_id, possible):
    """Cells the glacier may advance into by flooding below its terminus."""
    acc_glacier, gridyx, _, _ = terminus_shapes(grid, fdir, acc, gid, glacier_id)
    ncell = int(acc_glacier[acc_glacier > 0].size ** (2. / 3.))
    extend = np.zeros_like(gid)
    added = 0
    cellxy = (gridyx[1], gridyx[0])
    height = max(hand[cellxy[1], cellxy[0]], dem_surf[cellxy[1], cellxy[0]] - dem[cellxy[1], cellxy[0]], 50.0)
    possible0 = possible.copy()
    possible0[gid == glacier_id] = 1
    while added < ncell:
        step = NEXT_CELL[fdir[cellxy[1], cellxy[0]]]
        new_x, new_y = cellxy[0] + step[0], cellxy[1] + step[1]
        if not (0 <= new_y < possible.shape[0] and 0 <= new_x < possible.shape[1]) or possible0[new_y, new_x] != 1:
            break
        extend[new_y, new_x] = 1
        if gid[new_y, new_x] != glacier_id:
            added += 1
        cellxy = (new_x, new_y)
        extend, added = inundate(dem_surf, dem, (gridyx[1], gridyx[0]), gid, glacier_id, cellxy, possible0,
                                 hand, height, extend, ncell, added)
    print(f"glacier {glacier_id} extended by {added} cells to height {int(height)} m, {ncell} cells requested")
    return extend


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    p.add_argument("--method", choices=("drag", "fill"), default="drag")
    p.add_argument("--gru-threshold", type=float, default=0.8,
                   help="fraction of a glacier's cells inside the basin for it to be modelled")
    p.add_argument("--output-dir", help="write the rasters and basin here instead of the domain's folders")
    a = p.parse_args()
    sys.setrecursionlimit(max(sys.getrecursionlimit(), 100000))
    c = load_config(a.config)
    project, name = c["project_dir"], c["domain"]
    glacier_dir = os.path.join(project, "attributes", "glaciers")
    dem_dir = os.path.join(project, "attributes", "elevation", "dem")
    out_glacier = a.output_dir or glacier_dir
    out_basin = a.output_dir or os.path.join(project, "shapefiles", "river_basins")
    os.makedirs(out_glacier, exist_ok=True)
    os.makedirs(out_basin, exist_ok=True)

    lat, lon = (float(v) for v in c["pour_point"].split("/"))
    grid, dem, fdir, acc, catch = delineate(os.path.join(dem_dir, f"domain_{name}_bedrock_elv.tif"), lat, lon)
    polygons = [Polygon(s[0]["coordinates"][0]) for s in
                rasterio.features.shapes(np.where(catch, 1, 0).astype(np.uint8), transform=grid.affine) if s[1] == 1]
    basin = gpd.GeoDataFrame({"geometry": polygons}, crs=grid.crs).dissolve()
    basin["GRU_ID"] = 1
    basin["gru_to_seg"] = 1
    basin["GRU_area"] = basin.to_crs("epsg:3763").geometry.area  # m2, in the projection the domains were built with
    basin.to_crs("epsg:4326").to_file(os.path.join(out_basin, f"{name}_riverBasins_lumped.shp"))

    with rasterio.open(os.path.join(glacier_dir, f"domain_{name}_rgi_id.tif")) as src:
        gid = src.read(1)
        meta = src.meta.copy()
    with rasterio.open(os.path.join(glacier_dir, f"domain_{name}_domain_type.tif")) as src:
        dtype = src.read(1)
    with rasterio.open(os.path.join(dem_dir, f"domain_{name}_elv.tif")) as src:
        dem_surf = src.read(1)

    possible = np.zeros_like(gid)
    possible[catch == 1] = 1
    possible[((gid > 0) | dtype) != 1] = 0  # only into upland cells
    hand = grid.compute_hand(fdir, dem, acc > 100) if a.method == "fill" else None

    glaciers = [g for g in np.unique(gid) if g != 0
                and np.sum((gid == g) & catch) >= a.gru_threshold * np.sum(gid == g)]
    glaciers = np.array(glaciers)[np.argsort(np.bincount(gid.ravel())[glaciers])[::-1]] if glaciers else np.array([])
    for g in glaciers:
        if a.method == "drag":
            extend = drag(grid, fdir, acc, gid, g, possible)
        else:
            extend = fill(grid, dem, dem_surf, fdir, acc, hand, gid, g, possible)
        gid[extend == 1] = g
        possible[extend == 1] = 0

    gid[~np.isin(gid, glaciers)] = 0
    dtype[~np.isin(gid, glaciers)] = 1
    with rasterio.open(os.path.join(out_glacier, f"domain_{name}_domain_type_extend.tif"), "w", **meta) as dst:
        dst.write(dtype, 1)
    with rasterio.open(os.path.join(out_glacier, f"domain_{name}_rgi_id_extend.tif"), "w", **meta) as dst:
        dst.write(gid, 1)
    print(f"wrote the basin to {out_basin} and the extended rasters to {out_glacier}")


if __name__ == "__main__":
    main()
