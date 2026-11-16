"""WY2005 JJA mean longwave by HRU: ERA5 cell, current free-air T^4 scaling from ERA5's orography, the same
scaling from the forcing shapefile's elev_m (DEM mean of the cell within the old domain clip) and from the basin mean.

    /Users/amedin/miniconda3/envs/glacier/bin/python scratch/2026-11-16/lw_anchor_by_hru.py
"""
import glob, os, sys
import numpy as np
import geopandas as gpd
from netCDF4 import Dataset

sys.path.insert(0, os.getcwd())  # run from the workflow root
from remap_forcing import weights, read_levels, column, cell_elevation, CLEAR

for dom in ("Wolverine", "Gulkana"):  # the general domains share these ERA5 cells
    d, name = f"data/domain_{dom}", dom.split("_")[0]
    hrus = gpd.read_file(f"{d}/shapefiles/catchment/{name}_HRUs_elevation.shp").sort_values("HRU_ID")
    cells = gpd.read_file(f"{d}/shapefiles/forcing/forcing_ERA5.shp")
    raw = [f"{d}/forcing/raw_data/domain_{dom}_ERA5_merged_2005{m:02d}.nc" for m in (6, 7, 8)]
    with Dataset(raw[0]) as f:
        lat, lon = f["latitude"][:], f["longitude"][:]
    w = weights(hrus, lat, lon)
    zs = cell_elevation(f"{d}/forcing/raw_levels/domain_{dom}_ERA5_orography.nc", lat, lon)
    elev_m = np.full_like(zs, np.nan)
    for _, c in cells.iterrows():
        elev_m[np.argmin(abs(lat - c.lat)), np.argmin(abs(lon - c.lon))] = c.elev_m
    z = hrus.elev_mean.values
    acc = {k: np.zeros(len(z)) for k in ("cell", "new", "dem", "basin")}
    zb = np.average(z, weights=hrus.HRU_area)
    n = 0
    for path in raw:
        lpath = path.replace("raw_data", "raw_levels").replace("_merged_", "_levels_")
        with Dataset(path) as src:
            hours, lw = np.asarray(src["time"][:], dtype="f8"), np.asarray(src["LWRadAtm"][:], dtype="f8")
        lev = read_levels(lpath, lpath.replace(path[-9:-3], f"2005{int(path[-5:-3]) + 1:02d}"), hours)
        n += len(hours)
        for k, i, j in zip(*np.nonzero(w)):
            h, t = lev["h"][:, :, i, j], lev["t"][:, :, i, j]
            at = lambda zz: column(h, zz, zs[i, j] + CLEAR)(t)
            th = at(z[k])
            acc["cell"][k] += w[k, i, j] * lw[:, i, j].sum()
            acc["new"][k] += w[k, i, j] * (lw[:, i, j] * (th / at(zs[i, j])) ** 4).sum()
            acc["dem"][k] += w[k, i, j] * (lw[:, i, j] * (th / at(elev_m[i, j])) ** 4).sum()
            acc["basin"][k] += w[k, i, j] * (lw[:, i, j] * (th / at(zb)) ** 4).sum()
    print(f"\n{dom}: ERA5 surface under HRUs {np.round(np.sum(w * zs, axis=(1, 2)))}, elev_m {np.round(np.nansum(w * np.nan_to_num(elev_m), axis=(1, 2)))}")
    print(f" basin mean {zb:.0f} m\n HRU  elev   cell    new    dem  basin  basin-new")
    for k in range(len(z)):
        c, nw, dm, bs = (acc[x][k] / n for x in ("cell", "new", "dem", "basin"))
        print(f" {k + 1:3d} {z[k]:5.0f} {c:6.1f} {nw:6.1f} {dm:6.1f} {bs:6.1f} {bs - nw:6.1f}")
