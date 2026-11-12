#!/usr/bin/env python3
"""Flowline fetch (path length up the steepest ascent over ice to where the ice ends, as SUMMA's glacDomFetch)
at the Wilson 2024 sites on Gulkana, and the glacierCoolLength that gives Site B's cooling factor.

    site_fetch.py <domain dir> <site_locations.csv> <air_cooling csv>
"""
import sys, os, tempfile
import numpy as np, pandas as pd, rasterio
from rasterio.warp import transform as warp_xy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from glacier_cold_state import reproject_to_utm

dom, sites_csv, cool_csv = sys.argv[1:4]
name = os.path.basename(dom.rstrip("/")).replace("domain_", "")
surf_tif = os.path.join(dom, "attributes", "elevation", "dem", f"domain_{name}_glacier_elv_utm.tif")
bed_tif = os.path.join(dom, "attributes", "elevation", "dem", f"domain_{name}_bedrock_elv_utm.tif")
with rasterio.open(surf_tif) as r:
    S, T, crs = r.read(1).astype(float), r.transform, r.crs
with rasterio.open(bed_tif) as r:
    B = r.read(1).astype(float)
with tempfile.TemporaryDirectory() as tmp:
    reproject_to_utm(os.path.join(dom, "attributes", "glaciers", f"domain_{name}_rgi_id_extend.tif"), f"{tmp}/id.tif", crs.to_epsg())
    with rasterio.open(f"{tmp}/id.tif") as r:
        gid = r.read(1)
dx, dy = T.a, -T.e
sites = pd.read_csv(sites_csv, skipinitialspace=True)
sites.columns = ["site", "lat", "lon", "elev"]
xs, ys = warp_xy("EPSG:4326", crs, sites.lon.tolist(), sites.lat.tolist())
rows, cols = rasterio.transform.rowcol(T, xs, ys)
gB = gid[rows[list(sites.site).index("B")], cols[list(sites.site).index("B")]]
ice = (gid == gB) & (S - B > 1.0)
ny, nx = S.shape
fetch = np.zeros_like(S)
cells = np.flatnonzero(ice)
for c in cells[np.argsort(-S.ravel()[cells], kind="stable")]:
    k, j = divmod(c, nx)
    best, up = 0.0, None
    for dk in (-1, 0, 1):
        for dj in (-1, 0, 1):
            kn, jn = k + dk, j + dj
            if (dk or dj) and 0 <= kn < ny and 0 <= jn < nx and ice[kn, jn]:
                d = np.hypot(dj * dx, dk * dy)
                rise = (S[kn, jn] - S[k, j]) / d
                if rise > best:
                    best, up = rise, (kn, jn, d)
    if up:
        kn, jn, d = up
        fetch[k, j] = fetch[kn, jn] + d
print(f"glacier {gB}: {ice.sum()} ice cells of {dx:.0f} m, surface {S[ice].min():.0f}-{S[ice].max():.0f} m, longest fetch {fetch.max():.0f} m")
for s, k, j in zip(sites.site, rows, cols):
    win = ice[max(k-1,0):k+2, max(j-1,0):j+2]
    f = fetch[max(k-1,0):k+2, max(j-1,0):j+2][win]
    print(f"{s:9s} surface {S[k, j]:6.0f} m  fetch {fetch[k, j]:6.0f} m (3x3 ice cells {f.min() if f.size else np.nan:.0f}-{f.max() if f.size else np.nan:.0f})")
f_cool = pd.read_csv(cool_csv).set_index("month").loc["all", "factor"]
xB = fetch[rows[list(sites.site).index("B")], cols[list(sites.site).index("B")]]
print(f"Site B factor {f_cool:.4f} at fetch {xB:.0f} m -> glacierCoolLength {-xB/np.log(f_cool):.0f} m")
# mean fetch by 100 m elevation band, for comparison with SUMMA's DOMfetch
for z in range(int(S[ice].min()//100*100), int(S[ice].max())+100, 100):
    m = ice & (S >= z) & (S < z + 100)
    if m.any():
        print(f"  {z}-{z+100} m: {m.sum():5d} cells, mean fetch {fetch[m].mean():6.0f} m, factor {np.exp(fetch[m].mean()*np.log(f_cool)/xB):.2f}")
