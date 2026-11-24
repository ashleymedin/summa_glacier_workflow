#!/usr/bin/env python3
"""Split a domain's basin into the GRUs of its YAML's `grus:` list, from the USGS HUC12s (acquire_nhd.py) and the bed DEM.

Each entry is {name, huc12, above: [lon, lat]?, stream: <NHD gnis_name>?}: the part of the basin in that HUC12, or with `above`
only the part draining to the NHD `stream` at that point (on the surface DEM with the NHD flowlines burnt in --burn m, so it follows
NHD), taken from the cells the entries before it left; the last entry of a HUC12 takes what is left of it. A GRU's reach is the
next entry its water reaches: `to` names it, 0 (the default for the last) is the outlet. With `glaciers: [RGI ids]` in any entry
the ice of those glaciers and their advance room go to that GRU whatever the DEM says, and an ice-free cell to the GRU of the ice or
the `above` point (an unnamed stream's: no `stream`; `within` m of it, default 150) its water reaches first, else to the last entry. Writes

  shapefiles/catchment/<name>_GRUs.shp   GRU_ID (1, 2, ... in list order), name, to_GRU, GRU_area (m2)

which make_hrus.py then cuts into elevation bands.

    ./split_grus.py domains/slate_creek.yaml
"""

import argparse
import glob
import os

import geopandas as gpd
import numpy as np
import rasterio.features
from pysheds.grid import Grid
from shapely.geometry import Point, shape
from shapely.ops import unary_union

from domain_config import load_config


NEXT_CELL = {64: (-1, 0), 128: (-1, 1), 1: (0, 1), 2: (1, 1), 4: (1, 0), 8: (1, -1), 16: (0, -1), 32: (-1, -1)}


def glacier_owner(c, project, name, grid, fdir, acc, flow, rast, crs, cell_m, basin):
    """GRU number of every basin cell of a domain whose `grus:` name their glaciers."""
    grus = c["grus"]
    with rasterio.open(os.path.join(project, "attributes", "glaciers", f"domain_{name}_rgi_id_extend.tif")) as r:
        ids = r.read(1)
    owner = np.zeros(ids.shape, int)
    for k, g in enumerate(grus, start=1):
        for rgi in g.get("glaciers", []):
            owner[ids == int(rgi.split("-")[-1].replace(".", "")[-5:]) + 100000 * int(c["rgi6_region"][:2])] = k
    if np.any((ids > 0) & (owner == 0) & basin):
        raise SystemExit(f"glaciers {np.unique(ids[(ids > 0) & (owner == 0) & basin])} are in no GRU")
    on = rast(flow.geometry, True)
    for k, g in enumerate(grus, start=1):
        if "above" not in g:
            continue
        x, y = gpd.GeoSeries([Point(*g["above"])], crs=4326).to_crs(crs).iloc[0].coords[0]
        col, row = ~grid.affine * (x, y)
        dy, dx = abs(grid.affine.e) * 110574.0, abs(grid.affine.a) * 111320.0 * np.cos(np.radians(y))
        near = np.hypot((np.arange(ids.shape[0])[:, None] - row) * dy, (np.arange(ids.shape[1])[None, :] - col) * dx) < g.get("within", 150)
        cand = list(zip(*np.nonzero(on & near & (owner == 0))))
        i, j = max(cand, key=lambda t: acc[t])
        print(f"  GRU {k} outlet cell: accumulation {acc[i, j] * cell_m[i, j] / 1e6:.2f} km2 of {len(cand)} stream cells near {g['above']}")
        owner[i, j] = k
    F = np.asarray(fdir)
    order = np.argsort(np.where(basin, acc, -1), axis=None)[::-1]
    for flat in order[:int(basin.sum())]:  # downstream cells first
        i, j = np.unravel_index(flat, owner.shape)
        if owner[i, j] == 0:
            step = NEXT_CELL.get(int(F[i, j]))
            down = (i + step[0], j + step[1]) if step else None
            inside = down and 0 <= down[0] < owner.shape[0] and 0 <= down[1] < owner.shape[1] and basin[down]
            owner[i, j] = owner[down] if inside and owner[down] else len(grus)
    return np.where(basin, owner, 0)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    p.add_argument("--burn", type=float, default=20.0, help="m the NHD flowlines are lowered in the DEM")
    a = p.parse_args()
    c = load_config(a.config)
    project, name = c["project_dir"], c["domain"]
    dem_path = os.path.join(project, "attributes", "elevation", "dem", f"domain_{name}_elv.tif")  # geographic: the UTM copy can lack the outlet
    grid = Grid.from_raster(dem_path)
    dem = grid.read_raster(dem_path)
    with rasterio.open(dem_path) as r:
        crs = r.crs
    nhd = os.path.join(project, "shapefiles", "nhd.gpkg")
    huc = gpd.read_file(nhd, layer="huc12").to_crs(crs).set_index("huc12")
    flow = gpd.read_file(nhd, layer="flowlines").to_crs(crs)
    basin = gpd.read_file(glob.glob(os.path.join(project, "shapefiles", "river_basins", "*.shp"))[0]).to_crs(crs).union_all()
    rast = lambda geoms, touched=False: rasterio.features.rasterize([(g, 1) for g in geoms], out_shape=dem.shape, transform=grid.affine,
                                                                    all_touched=touched).astype(bool)
    z = dem.copy()
    z[rast(flow.geometry, True)] -= a.burn
    fdir = grid.flowdir(grid.resolve_flats(grid.fill_depressions(grid.fill_pits(z))))
    acc = np.asarray(grid.accumulation(fdir))
    left = rast([basin])
    lat = grid.affine.f + grid.affine.e * (np.arange(dem.shape[0]) + 0.5)
    cell_m = (abs(grid.affine.a) * 111320.0 * np.cos(np.radians(lat))[:, None] * abs(grid.affine.e) * 110574.0) * np.ones(dem.shape)  # m2
    rows = []
    owner = glacier_owner(c, project, name, grid, fdir, acc, flow, rast, crs, cell_m, left) if any("glaciers" in g for g in c["grus"]) else None
    for k, g in enumerate(c["grus"]):
        if owner is not None:
            part = left & (owner == k + 1)
            left &= ~part
            geom = unary_union([shape(s) for s, v in rasterio.features.shapes(part.astype(np.uint8), mask=part, transform=grid.affine) if v == 1])
            rows.append({"GRU_ID": k + 1, "name": g["name"], "to_GRU": int(g.get("to", 0)), "geometry": geom})
            print(f"GRU {k + 1} {g['name']}: {cell_m[part].sum() / 1e6:.2f} km2, to GRU {g.get('to', 0)}")
            continue
        part = left & rast([huc.loc[str(g["huc12"])].geometry.intersection(basin)])
        if "above" in g:
            x, y = gpd.GeoSeries([Point(*g["above"])], crs=4326).to_crs(crs).iloc[0].coords[0]
            on = rast(flow[flow.gnis_name == g["stream"]].geometry, True)
            col, row = ~grid.affine * (x, y)
            dy, dx = abs(grid.affine.e) * 110574.0, abs(grid.affine.a) * 111320.0 * np.cos(np.radians(y))
            near = np.hypot((np.arange(dem.shape[0])[:, None] - row) * dy, (np.arange(dem.shape[1])[None, :] - col) * dx) < 150
            ii, jj = np.nonzero(on & near)
            i, j = max(zip(ii, jj), key=lambda t: acc[t])  # the stream's largest accumulation within 150 m of the point
            above = np.asarray(grid.catchment(x=j, y=i, fdir=fdir, xytype="index")).astype(bool)
            print(f"  {g['stream']} near {g['above']}: {len(ii)} cells, outlet accumulation {acc[i, j] * cell_m[i, j] / 1e6:.1f} km2, catchment "
                  f"{cell_m[above].sum() / 1e6:.1f} km2, {cell_m[above & part].sum() / 1e6:.1f} km2 of it in the HUC12's remainder")
            part &= above
        left &= ~part
        geom = unary_union([shape(s) for s, v in rasterio.features.shapes(part.astype(np.uint8), mask=part, transform=grid.affine) if v == 1])
        rows.append({"GRU_ID": k + 1, "name": g["name"], "to_GRU": int(g.get("to", 0)), "geometry": geom})
        print(f"GRU {k + 1} {g['name']}: {cell_m[part].sum() / 1e6:.1f} km2, to GRU {g.get('to', 0)}")
    if left.any():
        print(f"{cell_m[left].sum() / 1e6:.2f} km2 of the basin in no GRU's HUC12")
    grus = gpd.GeoDataFrame(rows, crs=crs).to_crs(c["utm_crs"])
    grus["GRU_area"] = grus.geometry.area
    out = os.path.join(project, "shapefiles", "catchment", f"{name}_GRUs.shp")
    grus.to_file(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
