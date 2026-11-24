#!/usr/bin/env python3
"""Hugonnet et al. (2021) 2000-19 elevation change of each Lemon Creek glacier (RGI 6 outlines, mean; x 850 kg m-3) against the split runs' balances."""
import os, glob, numpy as np, geopandas as gpd, rasterio, netCDF4 as nc
from rasterio.features import geometry_mask
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ids = {"RGI60-01.01506": 0, "RGI60-01.01105": 1, "RGI60-01.01104": 2, "RGI60-01.01102": 2, "RGI60-01.01103": 2, "RGI60-01.25476": 2}
g = gpd.read_file(glob.glob("data/external/RGI_data/*rgi60*/*rgi60*.shp")[0], where=f"RGIId in {tuple(ids)}").set_index("RGIId")
for rid in ids:
    s = []
    for f in glob.glob("data/external/Hugonnet/01_02_rgi60_2000-01-01_2020-01-01/dhdt/N58W13[45]*.tif"):
        with rasterio.open(f) as r:
            q = gpd.GeoSeries([g.loc[rid].geometry], crs=g.crs).to_crs(r.crs).iloc[0]
            if not q.intersects(__import__("shapely").geometry.box(*r.bounds)): continue
            m = geometry_mask([q], out_shape=r.shape, transform=r.transform, invert=True); z = r.read(1)
            v = z[m & (z > -50) & (z < 50)]; s.append(v)
    v = np.concatenate(s); print(f"{rid} GRU {ids[rid] + 1}: dh/dt {v.mean():+.2f} m/yr, {v.mean() * 850:+.0f} mm w.e./yr ({len(v)} cells)")
d = nc.Dataset(glob.glob("runs/lemon_grus/test/length/output/*_day.nc")[0]); t = nc.num2date(d["time"][:], d["time"].units); y = np.array([x.year + (x.month > 9) for x in t]); m = np.ma.filled(d["basin__GlacierMassChange_mean"][:], 0) * 86400
for k in (2006, 2010, 2015, 2019, 2022, 2025): print(k, "annual balance per GRU mm", m[y == k].sum(0).round(0))
print("WY2006-19 mean", (m[(y >= 2006) & (y <= 2019)].sum(0) / 14).round(0))
o = nc.Dataset("runs/lemon_grus/test/one/output/" + "lemon_added_day.nc"); mo = np.ma.filled(o["basin__GlacierMassChange_mean"][:], 0).ravel() * 86400; print("one GRU WY2006-19", round(mo[(y >= 2006) & (y <= 2019)].sum() / 14))
# snowfall and melt of each glacier domain
A = np.ma.filled(d["DOMarea_mean"][:], 0); sn = np.ma.filled(d["scalarSnowfall_mean"][:], 0) * 86400; sel = (y >= 2006) & (y <= 2019); ty = np.ma.filled(d["domType"][:], 0)
z = np.ma.filled(d["DOMelev_mean"][:], 0); ml = np.ma.filled(d["scalarGlacierMelt_mean"][:], 0) * 86400 * 1000
for h, k in np.argwhere((ty == 2) | (ty == 3)): print(f"HRU {h + 1} dom {k + 1}: {z[sel][:, h, k].mean():.0f} m, {A[sel][:, h, k].mean() / 1e6:.2f} km2, snowfall {sn[sel][:, h, k].sum() / 14:.0f}, glacier melt {ml[sel][:, h, k].sum() / 14:.0f} mm/yr")
