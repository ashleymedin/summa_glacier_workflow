#!/usr/bin/env python3
"""Lemon Creek's three proglacial lakes: area, and a depth from the banks' topography, as the lakes are open water in every DEM
(Wolverine's lake_depth.py fills a bed that was under ice; here the DEM holds the water surface).

Water is NDWI > 0.1 and MNDWI > 0.1 in the 18 Aug 2024 Sentinel-2 scene, the patch of at least 30 pixels nearest each lake. Each lake cell takes the slope of the bank beside
it (2 m USGS DEM of 1 Oct 2018 on a 5 m grid, median rise 10-40 m from the shore, over the land nearest the cell within 60 m of its
shore point) times its distance to the shore; the lake's wedge is then limited by the opposite bank's. Beside it, Huggel et al. (2002)
V = 0.104 A^1.42. Writes nothing.
"""
import os
import numpy as np, planetary_computer, pystac_client, rasterio
from odc.geo.geobox import GeoBox
from odc.stac import load
from pyproj import Transformer
from rasterio.warp import Resampling, reproject
from scipy import ndimage

W = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
X, Y = Transformer.from_crs(4326, 32608, always_xy=True).transform([-134.3745, -134.3770, -134.3835], [58.4122, 58.4080, 58.4042])
gb = GeoBox.from_bbox((min(X) - 900, min(Y) - 900, max(X) + 900, max(Y) + 900), "EPSG:32608", resolution=5)
cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace)
it = cat.get_collection("sentinel-2-l2a").get_item("S2A_MSIL2A_20240818T201851_R071_T08VNK_20240819T014500")
ds = load([it], bands=["B03", "B08", "B11"], geobox=gb, resampling="bilinear")
g, n, s = (ds[b].values[0].astype(float) - 1000 for b in ("B03", "B08", "B11"))
water = ((g - n) / (g + n) > 0.1) & ((g - s) / (g + s) > 0.1) & (n < 2500)
water = ndimage.binary_opening(water, iterations=3)
dem = np.full(gb.shape, np.nan)
with rasterio.open(os.path.join(W, "data/external/GlacierDEM/JuneauIcefield_20181001_DEM/JuneauIcefield_20181001_DEM.tif")) as r:
    reproject(rasterio.band(r, 1), dem, dst_transform=gb.affine, dst_crs="EPSG:32608", resampling=Resampling.average, dst_nodata=np.nan)
lab, k = ndimage.label(water)
tot = []
for name, x, y in zip(("upper", "middle", "lower"), X, Y):
    c, r0 = ~gb.affine * (x, y)
    big = [i for i in range(1, k + 1) if (lab == i).sum() * 25 > 5000]
    i = min(big, key=lambda j: np.hypot(*(np.argwhere(lab == j) - (r0, c)).T).min())
    lake = lab == i
    A = lake.sum() * 25.0
    level = np.nanmedian(dem[lake])
    out, idx = ndimage.distance_transform_edt(~lake, return_indices=True)
    out *= 5
    ring = (out >= 10) & (out <= 40) & np.isfinite(dem) & ~water
    slope = np.clip((dem[ring] - np.nanpercentile(dem[lake], 25)) / out[ring], 0, 1.5)
    pts = np.argwhere(ring) * 5.0
    inner, jdx = ndimage.distance_transform_edt(lake, return_indices=True)
    inner *= 5
    depth = np.zeros(lake.shape)
    for a, b in np.argwhere(lake):  # the bank slope near the cell's shore point
        sh = jdx[:, a, b] * 5.0
        near = np.hypot(*(pts - sh).T) < 60
        depth[a, b] = inner[a, b] * (np.median(slope[near]) if near.any() else np.median(slope))
    d = depth[lake]
    huggel = 0.104 * A ** 1.42 / A
    order = np.sort(d)[::-1]
    h = order[0] - order
    use = (h > 0) & (np.arange(1, len(h) + 1) > 0.1 * len(h))
    shp = np.polyfit(np.log(np.arange(1, len(h) + 1)[use]), np.log(h[use]), 1)[0]
    print(f"{name}: {A:.0f} m2, DEM at the water {np.nanpercentile(dem[lake], [5, 50, 95]).round(1)} m, bank slope median {np.median(slope):.2f} "
          f"(quartiles {np.percentile(slope, 25):.2f}-{np.percentile(slope, 75):.2f}), bank depth mean {d.mean():.1f} max {d.max():.1f} m, "
          f"with the lower-quartile slope {inner[lake].mean() * np.percentile(slope, 25):.1f} m, Huggel {huggel:.1f} m, stage ~ area**{shp:.2f}")
    tot.append((A, d.mean(), huggel, level, shp))
t = np.array(tot)
print(f"all: {t[:, 0].sum():.0f} m2, area-weighted depth {np.average(t[:, 1], weights=t[:, 0]):.1f} m (banks), {np.average(t[:, 2], weights=t[:, 0]):.1f} m (Huggel), "
      f"elevation {np.average(t[:, 3], weights=t[:, 0]):.0f} m, shape {np.average(t[:, 4], weights=t[:, 0]):.2f}")
