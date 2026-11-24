#!/usr/bin/env python3
"""Lemon Creek: reach length from the main tongue's stream, the lakes' share of the water, one mixed lake against three in series, and
the glacier reservoirs with one k against a k of their own for the northern and Ptarmigan glaciers (default run, daily)."""
import os
import geopandas as gpd, netCDF4 as nc, numpy as np
from shapely.geometry import Point
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
l = gpd.read_file("data/domain_LemonCreek/shapefiles/nhd.gpkg", layer="reach").to_crs(32608).geometry.iloc[0]
join = l.length - l.project(Point(536200, 6473560))  # where the fan meets the stream below the lower lake
portal = [(536640, 6473660), (536470, 6473520), (536330, 6473560), (536200, 6473560)]
fan = sum(np.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(portal[:-1], portal[1:]))
print(f"reach now {l.length:.0f} m; below the fan {join:.0f} m + fan and stream to the ice {fan:.0f} m = {join + fan:.0f} m")
d = nc.Dataset("runs/lemon_added/default/output/lemon_added_day.nc")
a = np.ma.filled(d["DOMarea_mean"][:], 0).astype(float); m = np.ma.filled(d["scalarGlacierMelt_mean"][:], 0).astype(float)
a[(a < 0) | (a > 1e9)] = 0; m[abs(m) > 1] = 0
gla = np.ma.filled(d["basin__GlacierArea_mean"][:], 0).ravel()
q = np.ma.filled(d["glacierRoutedRunoff_mean"][:], 0).ravel()
t = np.array(d["time"][:]); units = d["time"].units
days = nc.num2date(t, units); mon = np.array([x.month for x in days])
tot = np.nansum(m * a, axis=(1, 2))  # m3/s if per unit domain area
print("glacier melt m3/s Jun-Sep (per domain area):", tot[(mon > 5) & (mon < 10)].mean().round(2), " routed glacier runoff x basin 31.9 km2:", (q * 31.9e6)[(mon > 5) & (mon < 10)].mean().round(2))
Qg = (q * 31.9e6)[(mon > 5) & (mon < 10)].mean(); share = 2.94 / 15.5; Qn = Qg * share
A = np.array([0.078, 0.055, 0.020]) * 1e6; V = 0.153e6 * 11
print(f"northern glacier {share:.0%} of the ice: {Qn:.2f} m3/s of {Qg:.2f}; residence of 1.7 Mm3 {V / Qn / 86400:.0f} days, with all the glacier water {V / Qg / 86400:.1f} days")
for Q, nm in ((Qn, "northern water only"), (Qg, "all glacier water")):
    for K in (20, 35):
        x = K * A / (4.2e6 * Q); one = x.sum() / (1 + x.sum()); three = 1 - np.prod(1 / (1 + x))
        print(f"  {nm}, K {K} W/m2/K: outlet warming towards equilibrium, one lake {one:.2f}, three in series {three:.2f}")
def res(x, k): # daily linear reservoir
    e = np.exp(-86400 / k); y = np.zeros_like(x); s = 0.
    for i, v in enumerate(x): s = s * e + v * (1 - e); y[i] = s
    return y
tot = np.maximum(tot, 0); share2 = (2.94 + 1.33) / 15.5
for nm, k in (("ice 15 h", 54e3), ("snow 90 h", 324e3), ("firn 575 h", 2070e3)):
    q1 = res(tot, k); q2 = (1 - share2) * q1 + share2 * res(tot, k / 2)
    print(f"reservoir {nm}: daily NSE of a half-size k on {share2:.0%} of the melt against one k: {1 - ((q2 - q1)**2).sum() / ((q1 - q1.mean())**2).sum():.4f}, rms {np.sqrt(((q2 - q1)**2).mean()) / q1.mean():.1%} of the mean")
