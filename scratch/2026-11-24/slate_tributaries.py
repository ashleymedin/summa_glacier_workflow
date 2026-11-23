#!/usr/bin/env python3
"""Tributaries of Slate Creek above USGS 15564879 by drainage area at their mouths, on the bed DEM (UTM), for choosing GRUs.

    slate_tributaries.py
"""
import os
import numpy as np
from pysheds.grid import Grid
from scipy import ndimage

WF = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
dem_path = os.path.join(WF, "data/domain_SlateCreek/attributes/elevation/dem/domain_SlateCreek_bedrock_elv_utm.tif")
grid = Grid.from_raster(dem_path)
dem = grid.read_raster(dem_path)
cond = grid.resolve_flats(grid.fill_depressions(grid.fill_pits(dem)))
fdir = grid.flowdir(cond)
acc = grid.accumulation(fdir)
cell = abs(grid.affine.a * grid.affine.e) / 1e6  # km2
x, y = grid.affine * (0, 0)
import pyproj
gx, gy = pyproj.Transformer.from_crs(4326, 32606, always_xy=True).transform(-150.1772222, 67.2544444)
sx, sy = grid.snap_to_mask(acc > 50 / cell, [(gx, gy)])[0]
basin = grid.catchment(x=sx, y=sy, fdir=fdir, xytype="coordinate")
A = np.where(basin, np.asarray(acc) * cell, 0.0)
print(f"basin at the gauge {A.max():.1f} km2, cell {cell * 1e6:.0f} m2")
# D8 directions (pysheds default dirmap N NE E SE S SW W NW = 64 128 1 2 4 8 16 32)
step = {64: (-1, 0), 128: (-1, 1), 1: (0, 1), 2: (1, 1), 4: (1, 0), 8: (1, -1), 16: (0, -1), 32: (-1, -1)}
fd = np.asarray(fdir)
for thr in (2, 5, 10, 20):
    stream = A >= thr
    mouths = []
    for i, j in zip(*np.nonzero(stream)):
        d = step.get(int(fd[i, j]))
        if d is None:
            continue
        ii, jj = i + d[0], j + d[1]
        if 0 <= ii < A.shape[0] and 0 <= jj < A.shape[1] and A[ii, jj] >= thr:
            # a confluence: the cell downstream has another stream cell flowing into it
            continue
    # count stream links: number of stream heads above the threshold is the Strahler-1 count
    heads = 0
    inflow = np.zeros_like(A, dtype=int)
    for i, j in zip(*np.nonzero(stream)):
        d = step.get(int(fd[i, j]))
        if d:
            ii, jj = i + d[0], j + d[1]
            if 0 <= ii < A.shape[0] and 0 <= jj < A.shape[1] and stream[ii, jj]:
                inflow[ii, jj] += 1
    conf = np.argwhere(inflow >= 2)
    # each confluence's smaller incoming branch areas
    tribs = []
    for ii, jj in conf:
        ins = []
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                i, j = ii + di, jj + dj
                if (di or dj) and 0 <= i < A.shape[0] and 0 <= j < A.shape[1] and stream[i, j]:
                    d = step.get(int(fd[i, j]))
                    if d and (i + d[0], j + d[1]) == (ii, jj):
                        ins.append(A[i, j])
        ins.sort()
        tribs.append(ins[:-1])
    small = sorted(a for t in tribs for a in t)[::-1]
    print(f"threshold {thr:>3} km2: {len(conf)} confluences, {len(conf) * 2 + 1} links; tributary areas at mouths (km2): {[round(a, 1) for a in small[:15]]}")
