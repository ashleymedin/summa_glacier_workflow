#!/usr/bin/env python3
"""Which lakes the water of each Lemon Creek glacier passes, and how much land drains to each lake: D8 on the USGS DEM of
1 Oct 2018 (2 m, averaged to 10 m; the bed and Copernicus outside it), depressions filled. Saves a map of the flow paths on the 2024 scene."""
import os, sys
import geopandas as gpd, numpy as np, rasterio, glob
from pysheds.grid import Grid
from pyproj import Transformer
from rasterio.warp import Resampling, reproject, transform_bounds
from rasterio.transform import from_origin
W = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
os.chdir(W); sys.path.insert(0, W)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from plot_proglacial import sentinel2
T = Transformer.from_crs(4326, 32608, always_xy=True)
p = "data/domain_LemonCreek/"
basin = gpd.read_file(glob.glob(p + "shapefiles/river_basins/*.shp")[0]).to_crs(32608)
x0, y0, x1, y1 = basin.total_bounds; res = 10
tr = from_origin(x0 - 400, y1 + 400, res, res); nx, ny = int((x1 - x0 + 800) / res), int((y1 - y0 + 800) / res)
def warp(f, how):
    out = np.full((ny, nx), np.nan)
    with rasterio.open(f) as r:
        reproject(rasterio.band(r, 1), out, dst_transform=tr, dst_crs="EPSG:32608", resampling=how, dst_nodata=np.nan)
    return out
cop = warp(sorted(glob.glob("data/external/Copernicus_GLO30/*W135*DEM.tif"))[0], Resampling.bilinear)
us = warp("data/external/GlacierDEM/JuneauIcefield_20181001_DEM/JuneauIcefield_20181001_DEM.tif", Resampling.average)
print("2018 DEM covers", np.isfinite(us).mean().round(2), "median offset to Copernicus", np.nanmedian(cop - us).round(1))
for label, z in (("2018 DEM", np.where(np.isfinite(us), us - 7.3, cop)), ("Copernicus 30 m", cop)):
    tmp = os.path.join(os.environ.get("TMPDIR", "/tmp"), "lemon_route.tif")
    with rasterio.open(tmp, "w", driver="GTiff", height=ny, width=nx, count=1, dtype="float64", crs="EPSG:32608", transform=tr, nodata=-9999) as d:
        d.write(np.where(np.isfinite(z), z, -9999), 1)
    g = Grid.from_raster(tmp); d = g.read_raster(tmp)
    fd = g.flowdir(g.resolve_flats(g.fill_depressions(g.fill_pits(d)))); acc = np.asarray(g.accumulation(fd)); F = np.asarray(fd)
    ll = gpd.read_file(p + "shapefiles/nhd.gpkg", layer="waterbodies").to_crs(32608); ll.columns = [c.lower() for c in ll.columns]
    step = {64: (-1, 0), 128: (-1, 1), 1: (0, 1), 2: (1, 1), 4: (1, 0), 8: (1, -1), 16: (0, -1), 32: (-1, -1)}
    lakes = {}
    for nm, lo, la, rad in (("upper", -134.3745, 58.4122, 140), ("middle", -134.3755, 58.4077, 130), ("lower", -134.3813, 58.4035, 120), ("tarn", -134.3912, 58.39377, 70)):
        X, Y = T.transform(lo, la); yy, xx = np.mgrid[0:ny, 0:nx]
        lakes[nm] = np.hypot(tr.c + (xx + .5) * res - X, tr.f - (yy + .5) * res - Y) < rad
        flat = lakes[nm]
        m = np.where(flat, acc, -1); i, j = np.unravel_index(m.argmax(), m.shape)
        c = np.asarray(g.catchment(x=j, y=i, fdir=fd, xytype="index")) > 0
        print(f"{label}: {nm} lake's largest accumulation {acc[i, j] * res * res / 1e6:.2f} km2")
    rgi = gpd.read_file("data/external/RGI_data/nsidc0770_01.rgi60.Alaska/01_rgi60_Alaska.shp", bbox=tuple(basin.to_crs(4326).total_bounds)).to_crs(32608).set_index("RGIId")
    for gid in ("RGI60-01.01104", "RGI60-01.01506", "RGI60-01.01105", "RGI60-01.01103", "RGI60-01.01102", "RGI60-01.25476"):
        m = ~rasterio.features.geometry_mask([rgi.loc[gid].geometry], transform=tr, out_shape=(ny, nx))
        pts = np.argwhere(m)[::7]; hit = {k: 0 for k in lakes}
        for a, b in pts:
            seen = set(); r, c = a, b
            for _ in range(4000):
                for k in lakes:
                    if lakes[k][r, c]: seen.add(k)
                st = step.get(int(F[r, c]))
                if st is None: break
                r, c = r + st[0], c + st[1]
                if not (0 <= r < ny and 0 <= c < nx): break
            for k in seen: hit[k] += 1
        print(f"  {gid}: share of cells passing " + ", ".join(f"{k} {v / len(pts):.2f}" for k, v in hit.items()))
    cx, cy = T.transform(-134.3745, 58.4060); h = 1100
    fig, ax = plt.subplots(figsize=(11, 11)); ax.imshow(sentinel2("S2A_MSIL2A_20240818T201851_R071_T08VNK_20240819T014500", cx, cy, h, 32608), extent=[cx - h, cx + h, cy - h, cy + h])
    yy, xx = np.nonzero(acc * res * res > 1.5e5); ax.scatter(tr.c + (xx + .5) * res, tr.f - (yy + .5) * res, s=np.sqrt(acc[yy, xx]) / 8, c="red")
    gpd.read_file(p + "shapefiles/nhd.gpkg", layer="flowlines").to_crs(32608).plot(ax=ax, color="cyan", lw=1)
    ax.set_xlim(cx - h, cx + h); ax.set_ylim(cy - h, cy + h); fig.tight_layout(); fig.savefig(sys.argv[1] + ("/r18.png" if label[0] == "2" else "/rcop.png"), dpi=70)
