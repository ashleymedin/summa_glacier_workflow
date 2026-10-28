#!/usr/bin/env python3
"""Delineate a glacier basin on its bed and give each glacier room to advance downstream.

A glacier surface is convex, so the basin is delineated with pysheds on the bed DEM (glacier_rasters.py),
lumped above the gauge. Writes shapefiles/river_basins/<name>_riverBasins_lumped.shp and, in
attributes/glaciers, the glacier-capable versions of the type and RGI id rasters:

  domain_<name>_domain_type_extend.tif   glaciers less than --gru-threshold inside the basin made upland
  domain_<name>_rgi_id_extend.tif        each glacier's id extended over the cells it may advance into

With basin_within: huc12 in the YAML the basin is clipped to the HUC12 holding the gauge (acquire_nhd.py), and a glacier is modelled when
most of its area is in that watershed (the USGS decides where its runoff goes) and most of it drains to the gauge on the bed;
the basin then holds every modelled glacier whole. Advance room not joined to its glacier is dropped, and glaciers whose advance room
meets share one grid (under the id of the largest). --merge body also joins a glacier whose room reaches another glacier's body, as
the Root glacier's would the Kennicott's; the YAML's merge_glaciers sets it, and the default (room) leaves the Wolverine and Gulkana setups as they are. Without it the glacier needs --gru-threshold of its cells inside the basin.

Extension, largest glacier first, by --method:
  drag  the terminus (the glacier's highest-accumulation cells) is shifted cell by cell down the flow
        direction until it has added (glacier cells)^(2/3) cells or meets the basin edge or another glacier,
        taking no cell above the terminus surface
  fill  from the terminus, cells downstream and around it are flooded while their height above nearest
        drainage is below the terminus ice thickness (at least 50 m), to the same cell count

    ./glacier_extend.py domains/wolverine.yaml
"""

import argparse
import os
import sys

import geopandas as gpd
import numpy as np
from scipy import ndimage
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


def drag(grid, fdir, acc, gid, glacier_id, possible, surface):
    """Cells the glacier may advance into by dragging its terminus downstream, none above the terminus surface."""
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
    below = surface <= surface[gridyx]  # the terminus piece can reach up the margins
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
        claim = (new_shape == 1) & (possible0 == 1) & below  # never onto another glacier or out of the basin
        extend[claim] = 1
        added += (claim & (possible == 1)).sum()  # only cells not already glacier
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
    p.add_argument("--merge", choices=("room", "body", "none"),
                   help="glaciers that share one grid: room (advance room meets advance room, the default), body (also advance room that "
                        "reaches another glacier's body, as the Root glacier into the Kennicott), or none; the YAML's merge_glaciers is the default")
    p.add_argument("--no-merge", action="store_true", help="same as --merge none")
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
    watershed = os.path.join(project, "shapefiles", "nhd.gpkg")
    if c.get("basin_within") == "huc12" and not os.path.exists(watershed):
        print(f"basin_within is set but {watershed} is missing (acquire_nhd.py is US only): the basin is the delineated one, "
              f"glaciers need --gru-threshold of their cells in it")
    if c.get("basin_within") == "huc12" and os.path.exists(watershed):  # the bed puts some divides in the wrong place; the USGS watershed of the gauge bounds the basin
        huc = gpd.read_file(os.path.join(project, "shapefiles", "nhd.gpkg"), layer="huc12")
        huc = huc[huc["gauge"] == 1].to_crs(grid.crs).geometry
        inside = rasterio.features.geometry_mask(list(huc), out_shape=catch.shape, transform=grid.affine, invert=True)
        print(f"basin clipped to the gauge's HUC12: {int(np.sum(catch))} to {int(np.sum(np.asarray(catch) & inside))} cells")
        catch = np.asarray(catch) & inside
    else:
        inside = None
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

    def modelled(g):
        """With the gauge's HUC12, a glacier is modelled if most of its area is in that watershed and most of it drains to the gauge on
        the bed; otherwise (no watershed data) if --gru-threshold of its cells are inside the basin."""
        cells = gid == g
        if inside is not None:
            return np.sum(cells & inside) > 0.5 * np.sum(cells) and np.sum(cells & catch) > 0.5 * np.sum(cells)
        return np.sum(cells & catch) >= a.gru_threshold * np.sum(cells)

    glaciers = [g for g in np.unique(gid) if g != 0 and modelled(g)]
    for g in np.unique(gid[gid > 0]):
        if g not in glaciers:
            print(f"glacier {int(g)} not modelled: {np.sum((gid == g) & catch) / np.sum(gid == g):.0%} of its cells in the basin"
                  + (f", {np.sum((gid == g) & inside) / np.sum(gid == g):.0%} in the gauge's HUC12" if inside is not None else ""))
    glaciers = np.array(glaciers)[np.argsort(np.bincount(gid.ravel())[glaciers])[::-1]] if glaciers else np.array([])
    original = gid.copy()
    eight = np.ones((3, 3))
    for g in glaciers:
        if a.method == "drag":
            extend = drag(grid, fdir, acc, gid, g, possible, dem_surf)
        else:
            extend = fill(grid, dem, dem_surf, fdir, acc, hand, gid, g, possible)
        label, _ = ndimage.label((gid == g) | (extend == 1), structure=eight)
        joined = np.isin(label, np.unique(label[gid == g]))  # room to advance has to join the glacier
        if np.sum((extend == 1) & ~joined):
            print(f"glacier {int(g)}: {int(np.sum((extend == 1) & ~joined))} cells of advance room not joined to the glacier dropped")
        extend = np.where((extend == 1) & joined, 1, 0)
        gid[extend == 1] = g
        possible[extend == 1] = 0

    gid[~np.isin(gid, glaciers)] = 0
    dtype[~np.isin(gid, glaciers)] = 1
    mode = "none" if a.no_merge else (a.merge or c.get("merge_glaciers", "room"))
    if mode != "none":  # glaciers whose advance room meets flow as one: one grid, under the id of the largest
        room = {int(g): (gid == g) & (original != g) for g in glaciers}
        group = {g: g for g in room}
        def root(g):
            while group[g] != g:
                g = group[g]
            return g
        for g in room:
            near = ndimage.binary_dilation(room[g], structure=eight)
            for h in room:
                meet = near & room[h] if h > g else None
                if mode == "body":  # advance room that reaches the other glacier's own body, either way
                    meet = (near & ((original == h) | room[h])) | (ndimage.binary_dilation(room[h], structure=eight) & (original == g)) if h != g else None
                if meet is not None and np.any(meet) and root(g) != root(h):
                    group[root(h)] = root(g)
        for r in sorted({root(g) for g in room}):
            ids = [g for g in room if root(g) == r]
            if len(ids) > 1:
                largest = max(ids, key=lambda g: np.sum(original == g))
                print(f"advance room of glaciers {ids} meets: one grid, {largest}")
                for g in ids:
                    gid[gid == g] = largest
    catch = np.asarray(catch) | (gid > 0)  # the basin holds every modelled glacier whole
    with rasterio.open(os.path.join(out_glacier, f"domain_{name}_domain_type_extend.tif"), "w", **meta) as dst:
        dst.write(dtype, 1)
    with rasterio.open(os.path.join(out_glacier, f"domain_{name}_rgi_id_extend.tif"), "w", **meta) as dst:
        dst.write(gid, 1)
    polygons = [Polygon(s[0]["coordinates"][0]) for s in
                rasterio.features.shapes(np.where(catch, 1, 0).astype(np.uint8), transform=grid.affine) if s[1] == 1]
    basin = gpd.GeoDataFrame({"geometry": polygons}, crs=grid.crs).dissolve()
    basin["GRU_ID"] = 1
    basin["gru_to_seg"] = 1
    basin["GRU_area"] = basin.to_crs(c["utm_crs"]).geometry.area  # m2
    basin.to_crs("epsg:4326").to_file(os.path.join(out_basin, f"{name}_riverBasins_lumped.shp"))
    print(f"wrote the basin to {out_basin} and the extended rasters to {out_glacier}")


if __name__ == "__main__":
    main()
