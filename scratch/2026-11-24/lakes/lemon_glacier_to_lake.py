#!/usr/bin/env python3
"""Which RGI glaciers of the Lemon Creek domain drain through its proglacial lakes: D8 path from each glacier's lowest cell."""
import geopandas as gpd, numpy as np, rasterio, rasterio.features
from pysheds.grid import Grid

D = "data/domain_LemonCreek"
IDS = ["RGI60-01.01102", "RGI60-01.01103", "RGI60-01.01104", "RGI60-01.01105", "RGI60-01.25476"]
dem_path = f"{D}/attributes/elevation/dem/domain_LemonCreek_elv.tif"
grid = Grid.from_raster(dem_path)
dem = grid.read_raster(dem_path)
crs = rasterio.open(dem_path).crs
flow = gpd.read_file(f"{D}/shapefiles/nhd.gpkg", layer="flowlines").to_crs(crs)
rast = lambda gs: rasterio.features.rasterize([(g, 1) for g in gs], out_shape=dem.shape, transform=grid.affine, all_touched=True).astype(bool)
z = dem.copy()
z[rast(flow.geometry)] -= 20.0  # burnt in as split_grus.py does
fdir = np.asarray(grid.flowdir(grid.resolve_flats(grid.fill_depressions(grid.fill_pits(z)))))
step = {64: (-1, 0), 128: (-1, 1), 1: (0, 1), 2: (1, 1), 4: (1, 0), 8: (1, -1), 16: (0, -1), 32: (-1, -1)}
basin = gpd.read_file(f"{D}/shapefiles/catchment/LemonCreek_HRUs_GRUs.shp").to_crs(crs).union_all()
w = gpd.read_file(f"{D}/shapefiles/nhd.gpkg", layer="waterbodies").to_crs(crs)
w = w[(w.to_crs(32608).area < 1e6) & w.intersects(basin)].reset_index(drop=True)
km2 = w.to_crs(32608).area / 1e6
lake = np.zeros(dem.shape, int)
for k, g in enumerate(w.geometry, 1):
    lake[rast([g])] = k
rgi = gpd.read_file("data/external/RGI_data/nsidc0770_01.rgi60.Alaska/01_rgi60_Alaska.shp")
for _, r in rgi[rgi.RGIId.isin(IDS)].to_crs(crs).iterrows():
    m = rast([r.geometry])
    i, j = np.unravel_index(np.argmin(np.where(m, np.asarray(dem), np.inf)), dem.shape)
    hit = []
    for _ in range(5000):
        s = step.get(int(fdir[i, j]))
        if not s:
            break
        i, j = i + s[0], j + s[1]
        if not (0 <= i < dem.shape[0] and 0 <= j < dem.shape[1]):
            break
        if lake[i, j] and (not hit or hit[-1] != lake[i, j]):
            hit.append(int(lake[i, j]))
    name = r.Name if isinstance(r.Name, str) else ""
    print(f"{r.RGIId} {name} {r.Area:.2f} km2: through lakes {[round(km2[k - 1], 3) for k in hit] or 'none'}")
