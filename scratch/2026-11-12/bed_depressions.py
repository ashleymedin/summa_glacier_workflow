#!/usr/bin/env python3
"""Closed depressions of a case's glacier bed grids, to see whether the bed holds the proglacial lake.

Fills the bed of each glacier grid to its spill level (priority flood) and lists every depression of at least
--min-cells: area, depth, bed elevation, the HRU, how many cells start under ice, its centre, and which lake_area
boxes of the domain yaml it overlaps. With --run, also the depression's ice-free area at each year's end of that run.

    ./bed_depressions.py wolverine ../../runs/wolverine_added/summa_inputs --run ../../runs/wolverine_added/calibration_rerun/sample_460
"""

import argparse
import glob
import heapq
import os
import sys

import netCDF4 as nc4
import numpy as np
from pyproj import Transformer
from scipy import ndimage

GLACIER = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, GLACIER)
from compare_glacier_change import yearly  # noqa: E402
from domain_config import load_config  # noqa: E402
from glacier_cold_state import grid_transforms  # noqa: E402


def fill(z):
    """z raised to the level its water spills off the grid edge, or into a cell with no bed, at."""
    ny, nx = z.shape
    out, done, heap = z.copy(), np.zeros(z.shape, bool), []
    z = np.where(np.isnan(z), -np.inf, z)
    for j, i in np.argwhere(np.pad(np.zeros((ny - 2, nx - 2), bool), 1, constant_values=True) | np.isinf(z)):
        done[j, i] = True
        heapq.heappush(heap, (z[j, i], j, i))
    while heap:
        h, j, i = heapq.heappop(heap)
        for b, a in ((j - 1, i), (j + 1, i), (j, i - 1), (j, i + 1), (j - 1, i - 1), (j + 1, i + 1), (j - 1, i + 1), (j + 1, i - 1)):
            if 0 <= b < ny and 0 <= a < nx and not done[b, a]:
                out[b, a], done[b, a] = max(z[b, a], h), True
                heapq.heappush(heap, (out[b, a], b, a))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("domain", help="domain yaml name, e.g. wolverine")
    p.add_argument("inputs", help="summa_inputs folder with attributes.nc and coldState.nc")
    p.add_argument("--run", help="a rerun trial folder with yearly glacier grids in output/")
    p.add_argument("--min-cells", type=int, default=3)
    p.add_argument("--min-depth", type=float, default=0.5, help="fill depth that counts as depression (m)")
    a = p.parse_args()

    c = load_config(os.path.join(GLACIER, "domains", a.domain + ".yaml"))
    transforms, crs = grid_transforms(c["project_dir"], c["domain"], c["utm_epsg"])
    S, years = None, []
    if a.run:
        S, _, years = yearly(sorted(glob.glob(os.path.join(a.run, "output", "*sample*_annual.nc"))))
    to_lonlat = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    boxes = c.get("observations", {}).get("lake_area", [])

    with nc4.Dataset(os.path.join(a.inputs, "attributes.nc")) as at, nc4.Dataset(os.path.join(a.inputs, "coldState.nc")) as cs:
        for g, gid in enumerate(np.array(at["gridId"][:, 0])):
            ny, nx, dx = int(at["ny"][g, 0]), int(at["nx"][g, 0]), float(at["dx"][g, 0])
            bed = np.array(at["bed_elev"][:ny, :nx, g, 0], float)
            ice = np.array(cs["surface_elev"][:ny, :nx, g, 0], float) - bed
            hru = np.array(at["cell2hruId"][:ny, :nx, g, 0])
            depth = np.nan_to_num(fill(bed) - bed)
            label, n = ndimage.label(depth > a.min_depth, structure=np.ones((3, 3)))
            print(f"grid {gid}: {nx} x {ny} cells of {dx:.0f} m")
            for k in range(1, n + 1):
                m = label == k
                if m.sum() < a.min_cells:
                    continue
                rows, cols = np.where(m)
                x, y = transforms[int(gid)] * (cols.mean() + 0.5, rows.mean() + 0.5)
                lon, lat = to_lonlat.transform(x, y)
                lons, lats = to_lonlat.transform(*(transforms[int(gid)] * (cols + 0.5, rows + 0.5)))
                hit = [b["name"] for b in boxes if np.any((lons >= b["box"][0]) & (lons <= b["box"][2]) & (lats >= b["box"][1]) & (lats <= b["box"][3]))]
                print(f"  {m.sum() * dx * dx * 1e-6:6.3f} km2  depth max {depth[m].max():5.1f} mean {depth[m].mean():5.1f} m  "
                      f"volume {depth[m].sum() * dx * dx * 1e-6:6.2f} Mm3  bed {bed[m].min():5.0f}-{bed[m].max():5.0f} m  spill {bed[m].min() + depth[m].max():5.0f} m  "
                      f"HRU {','.join(str(v) for v in np.unique(hru[m]))}  under ice {(ice[m] > 1).sum()}/{m.sum()} (mean {ice[m].mean():4.0f} m)  "
                      f"at {lon:.4f}, {lat:.4f}  {' '.join(hit)}")
                if S is not None and (ice[m] > 1).any():
                    free = [(S[k, :ny, :nx, g] - bed <= 1)[m].sum() * dx * dx * 1e-6 for k in range(len(years))]
                    print("    ice-free km2 by year: " + "  ".join(f"{y} {v:.3f}" for y, v in zip(years, free)))


if __name__ == "__main__":
    main()
