#!/usr/bin/env python3
"""Lemon Creek domain check: surface DEM, basin, HRUs, glacier extent with advance room, NHD streams and lakes, gauge."""

import os

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import LightSource

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "..", "..", "data", "domain_LemonCreek")

with rasterio.open(os.path.join(P, "attributes/elevation/dem/domain_LemonCreek_glacier_elv.tif")) as s:
    dem, b = s.read(1).astype(float), s.bounds
with rasterio.open(os.path.join(P, "attributes/glaciers/domain_LemonCreek_domain_type_extend.tif")) as s:
    dtype = s.read(1)
with rasterio.open(os.path.join(P, "attributes/glaciers/domain_LemonCreek_domain_type.tif")) as s:
    dtype0 = s.read(1)
ext = (b.left, b.right, b.bottom, b.top)
hrus = gpd.read_file(os.path.join(P, "shapefiles/catchment/LemonCreek_HRUs_elevation.shp"))
basin = gpd.read_file(os.path.join(P, "shapefiles/river_basins/LemonCreek_riverBasins_lumped.shp"))
nhd = os.path.join(P, "shapefiles/nhd.gpkg")
flow, lakes, huc = (gpd.read_file(nhd, layer=l) for l in ("flowlines", "waterbodies", "huc12"))
lakes = lakes[lakes["FTYPE"] == 390]  # lakes and ponds, not the ice masses

fig, ax = plt.subplots(figsize=(9, 7.5))
shade = LightSource(315, 35).hillshade(dem, vert_exag=1.5, dx=55, dy=93)
ax.imshow(shade, cmap="gray", extent=ext, alpha=0.9)
ax.imshow(np.ma.masked_equal((dtype0 > 1).astype(int), 0), cmap="Blues", vmin=0, vmax=1.6, alpha=0.55, extent=ext)
ax.imshow(np.ma.masked_equal(((dtype > 1) & (dtype0 <= 1)).astype(int), 0), cmap="Purples", vmin=0, vmax=1.3, alpha=0.6, extent=ext)
huc.boundary.plot(ax=ax, color="0.5", lw=0.6, ls=":")
hrus.boundary.plot(ax=ax, color="orange", lw=1.0)
basin.boundary.plot(ax=ax, color="red", lw=1.8)
flow.plot(ax=ax, color="tab:blue", lw=0.7)
lakes.plot(ax=ax, color="tab:cyan", edgecolor="tab:blue", lw=0.5)
for r in hrus.itertuples():
    c = r.geometry.representative_point()
    ax.text(c.x, c.y, f"HRU {r.HRU_ID}\n{r.elev_mean:.0f} m", ha="center", fontsize=8, color="darkorange", weight="bold")
for r in lakes[lakes.to_crs(32608).area > 2e4].itertuples():
    c = r.geometry.representative_point()
    if b.left < c.x < b.right and b.bottom < c.y < b.top:
        ax.text(c.x, c.y, f"{gpd.GeoSeries([r.geometry], crs=4326).to_crs(32608).area.iloc[0] / 1e6:.3f} km²", fontsize=7, color="navy")
ax.plot(-134.4226873, 58.3915312, "k^", ms=9)
ax.text(-134.4226873, 58.3935, "USGS 15052000", fontsize=8)
ax.set_xlim(b.left, b.right); ax.set_ylim(b.bottom, b.top)
ax.set_aspect(1 / np.cos(np.radians(58.4)))
ax.set_title(f"Lemon Creek: basin {basin.to_crs(32608).area.sum() / 1e6:.1f} km² (red), HRUs (orange), "
             "2004 glacier (blue), advance room (purple)", fontsize=9)
out = os.path.join(HERE, "lemon_basin_check.png")
fig.savefig(out, dpi=130, bbox_inches="tight")
print(out)
