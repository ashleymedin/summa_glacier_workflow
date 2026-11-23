#!/usr/bin/env python3
"""Flow routing of Slate Creek on the bed DEM with the NHD flowlines burnt in (lowered --burn m) and the ground outside the
outlet taken as the basin's largest accumulation, so the network follows NHD; then the drainage area at the gauge, at the Myrtle Creek mouth, through
each NHD lake, and the tributaries by size. Writes the flow direction and accumulation to scratch/2026-11-24/slate_routing.npz.

    slate_routing.py
"""
import glob
import os

import geopandas as gpd
import numpy as np
import pyproj
import rasterio
import rasterio.features
from pysheds.grid import Grid

HERE = os.path.dirname(os.path.abspath(__file__))
WF = os.path.abspath(os.path.join(HERE, "..", ".."))
D = os.path.join(WF, "data/domain_SlateCreek")
BURN = 20.0
dem_path = os.path.join(D, "attributes/elevation/dem/domain_SlateCreek_bedrock_elv_utm.tif")
grid = Grid.from_raster(dem_path)
dem = grid.read_raster(dem_path)
nhd = os.path.join(D, "shapefiles/nhd.gpkg")
huc = gpd.read_file(nhd, layer="huc12").to_crs(32606)
basin = huc[huc.gauge == 1].union_all()
flow = gpd.read_file(nhd, layer="flowlines").to_crs(32606)
flow = flow[flow.intersects(basin.buffer(500))]
streams = rasterio.features.rasterize([(g, 1) for g in flow.geometry], out_shape=dem.shape, transform=grid.affine, all_touched=True)
inside = rasterio.features.geometry_mask([basin.buffer(100)], dem.shape, grid.affine, invert=True)
z = np.asarray(dem).astype(float).copy()
z[streams == 1] -= BURN
dem2 = dem.copy()
dem2[:] = z
fdir = grid.flowdir(grid.resolve_flats(grid.fill_depressions(grid.fill_pits(dem2))))
accR = grid.accumulation(fdir)
acc = np.asarray(accR).astype(float)
cell = abs(grid.affine.a * grid.affine.e) / 1e6
to_utm = pyproj.Transformer.from_crs(4326, 32606, always_xy=True)
to_ll = pyproj.Transformer.from_crs(32606, 4326, always_xy=True)
gx, gy = to_utm.transform(-150.1772222, 67.2544444)
bmask = rasterio.features.geometry_mask([basin], dem.shape, grid.affine, invert=True)
oi, oj = np.unravel_index(np.argmax(np.where(bmask, acc, -1)), acc.shape)  # Slate Creek's outlet, not the Koyukuk beside the gauge
sx, sy = grid.affine * (oj + 0.5, oi + 0.5)
catch = np.asarray(grid.catchment(x=oj, y=oi, fdir=fdir, xytype="index")).astype(bool)
print(f"outlet acc {acc[oi, oj] * cell:.1f} km2 at {to_ll.transform(sx, sy)}; gauge snapped {np.hypot(sx - gx, sy - gy):.0f} m; catchment {catch.sum() * cell:.1f} km2, HUC12s {bmask.sum() * cell:.1f} km2, "
      f"overlap {(catch & bmask).sum() * cell:.1f} km2")
for code, row in huc[huc.gauge == 1].set_index("huc12").iterrows():
    m = rasterio.features.geometry_mask([row.geometry], dem.shape, grid.affine, invert=True)
    print(f"HUC12 {code} {row.get('name', '')}: {m.sum() * cell:.1f} km2, {100 * (m & catch).sum() / m.sum():.0f}% in the catchment")
w = gpd.read_file(nhd, layer="waterbodies")
k = {x.lower(): x for x in w.columns}
w = w[w[k["ftype"]].astype(int) == 390].to_crs(32606)
w = w[w.intersects(basin)]
for _, lake in w.assign(a=w.area).sort_values("a", ascending=False).iterrows():
    m = rasterio.features.geometry_mask([lake.geometry.buffer(60)], acc.shape, grid.affine, invert=True)
    print(f"lake {lake[k['gnis_name']]} {lake.geometry.area / 1e6:.3f} km2: drains {acc[m & catch].max() * cell if (m & catch).any() else 0:.1f} km2")
# tributary mouths: confluences on the network where the smaller branch drains over 2 km2
step = {64: (-1, 0), 128: (-1, 1), 1: (0, 1), 2: (1, 1), 4: (1, 0), 8: (1, -1), 16: (0, -1), 32: (-1, -1)}
fd = np.asarray(fdir)
A = np.where(catch, acc * cell, 0.0)
net = A >= 2.0
tribs = []
for i, j in zip(*np.nonzero(net)):
    ins = []
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            ii, jj = i + di, j + dj
            if (di or dj) and 0 <= ii < A.shape[0] and 0 <= jj < A.shape[1] and net[ii, jj]:
                d = step.get(int(fd[ii, jj]))
                if d and (ii + d[0], jj + d[1]) == (i, j):
                    ins.append((A[ii, jj], ii, jj))
    if len(ins) >= 2:
        ins.sort()
        for a, ii, jj in ins[:-1]:
            x, y = grid.affine * (jj + 0.5, ii + 0.5)
            lon, lat = to_ll.transform(x, y)
            tribs.append((a, ins[-1][0], lon, lat))
tribs.sort(reverse=True)
print("tributaries over 2 km2 (area, main stem above, lon, lat):")
for t in tribs[:12]:
    print(f"  {t[0]:6.1f} km2 into {t[1]:6.1f} km2 at {t[2]:.4f} {t[3]:.4f}")
np.savez_compressed(os.path.join(HERE, "slate_routing.npz"), fdir=fd, acc=acc, catch=catch, transform=np.array(grid.affine)[:6])
