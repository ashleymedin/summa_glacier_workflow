#!/usr/bin/env python3
"""Drainage area through each NHD lake of Slate Creek (largest accumulation within 100 m of the lake, on the geographic surface
DEM: the UTM bed DEM has no low outlet), and the GRU each lies in.

    slate_lake_areas.py
"""
import os

import geopandas as gpd
import numpy as np
import rasterio
import rasterio.features
from pysheds.grid import Grid

WF = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
D = os.path.join(WF, "data/domain_SlateCreek")
p = os.path.join(D, "attributes/elevation/dem/domain_SlateCreek_elv.tif")
grid = Grid.from_raster(p)
dem = grid.read_raster(p)
acc = np.asarray(grid.accumulation(grid.flowdir(grid.resolve_flats(grid.fill_depressions(grid.fill_pits(dem))))))
lat = grid.affine.f + grid.affine.e * (np.arange(dem.shape[0]) + 0.5)
cell = abs(grid.affine.a) * 111320.0 * np.cos(np.radians(lat))[:, None] * abs(grid.affine.e) * 110574.0 / 1e6 * np.ones(dem.shape)
grus = gpd.read_file(os.path.join(D, "shapefiles/catchment/SlateCreek_GRUs.shp")).to_crs(4326)
w = gpd.read_file(os.path.join(D, "shapefiles/nhd.gpkg"), layer="waterbodies")
k = {x.lower(): x for x in w.columns}
w = w[w[k["ftype"]].astype(int) == 390].to_crs(32606)
w = w[w.intersects(grus.to_crs(32606).union_all())]
for _, lake in w.assign(a=w.area).sort_values("a", ascending=False).iterrows():
    g4326 = gpd.GeoSeries([lake.geometry.buffer(100)], crs=32606).to_crs(4326).iloc[0]
    m = rasterio.features.geometry_mask([g4326], acc.shape, grid.affine, invert=True)
    i, j = np.unravel_index(np.argmax(np.where(m, acc, -1)), acc.shape)
    gru = grus[grus.contains(gpd.GeoSeries([lake.geometry.centroid], crs=32606).to_crs(4326).iloc[0])]
    print(f"{lake[k['gnis_name']]} {lake.a / 1e6:.3f} km2 in {', '.join(gru.name) or 'no GRU'}: drains {acc[i, j] * cell[i, j]:.1f} km2")
