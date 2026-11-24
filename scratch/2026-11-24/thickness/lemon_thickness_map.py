#!/usr/bin/env python3
"""Lemon Creek's starting ice thickness (glacier surface minus bed, UTM 8N) with surface contours, the 1280 m station and the
2017 USGS outline, to place the Veitch et al. (2021) seismic line: flow-parallel at 352 deg, 1080-1150 m surface, near the centreline."""
import os
import geopandas as gpd
import matplotlib
import numpy as np
import pyproj
import rasterio
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
WF = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
D = os.path.join(WF, "data/domain_LemonCreek/attributes/elevation/dem")
s, b = (rasterio.open(os.path.join(D, f)) for f in ("domain_LemonCreek_glacier_elv_utm.tif", "domain_LemonCreek_bedrock_elv_utm.tif"))
S, B = s.read(1).astype(float), b.read(1).astype(float)
H = np.where(S - B > 1, S - B, np.nan)
ext = (s.bounds.left, s.bounds.right, s.bounds.bottom, s.bounds.top)
fig, ax = plt.subplots(figsize=(9, 10))
im = ax.imshow(H, extent=ext, cmap="viridis", vmin=0, vmax=400)
X, Y = np.meshgrid(np.linspace(ext[0], ext[1], S.shape[1]), np.linspace(ext[3], ext[2], S.shape[0]))
cs = ax.contour(X, Y, np.where(np.isfinite(H), S, np.nan), levels=[900, 1000, 1080, 1150, 1250], colors="w", linewidths=0.7)
ax.clabel(cs, fmt="%d", fontsize=7)
x, y = pyproj.Transformer.from_crs(4326, 32608, always_xy=True).transform(-134.366272, 58.367556)
ax.plot(x, y, "r^", ms=9)
plt.colorbar(im, ax=ax, label="ice thickness (m)")
ax.set_title("Lemon Creek starting thickness (Farinotti), surface contours; red: 1280 m station")
fig.savefig(os.path.join(HERE, "lemon_thickness_map.png"), dpi=110, bbox_inches="tight")
