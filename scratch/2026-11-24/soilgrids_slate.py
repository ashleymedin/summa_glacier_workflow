#!/usr/bin/env python3
"""SoilGrids 2.0 (ISRIC WCS) sand, silt and clay over each basin's upland (ground outside the glacier domains), 0-60 cm, with the
Carsel and Parrish (1988) hydraulic parameters of the USDA texture class of the mean, against the round-3 calibrated values.

    soilgrids_texture.py <download dir>
"""
import os
import subprocess
import sys

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

WF = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
BOX = {"SlateCreek": (-150.26, -149.62, 67.15, 67.36)}
DEPTHS = ["0-5cm", "5-15cm", "15-30cm", "30-60cm"]
WEIGHT = [5, 10, 15, 30]
# Carsel and Parrish (1988): theta_r, theta_s, alpha (m-1), n, Ks (m s-1)
CP = {"sand": (0.045, 0.43, 14.5, 2.68, 8.25e-5), "loamy sand": (0.057, 0.41, 12.4, 2.28, 4.05e-5),
      "sandy loam": (0.065, 0.41, 7.5, 1.89, 1.23e-5), "loam": (0.078, 0.43, 3.6, 1.56, 2.89e-6),
      "silt loam": (0.067, 0.45, 2.0, 1.41, 1.25e-6), "silt": (0.034, 0.46, 1.6, 1.37, 6.94e-7),
      "sandy clay loam": (0.100, 0.39, 5.9, 1.48, 3.64e-6), "clay loam": (0.095, 0.41, 1.9, 1.31, 7.22e-7),
      "silty clay loam": (0.089, 0.43, 1.0, 1.23, 1.94e-7), "sandy clay": (0.100, 0.38, 2.7, 1.23, 3.33e-7),
      "silty clay": (0.070, 0.36, 0.5, 1.09, 5.56e-8), "clay": (0.068, 0.38, 0.8, 1.09, 5.56e-7)}


def usda(sa, si, cl):
    if si + 1.5 * cl < 15: return "sand"
    if si + 2 * cl < 30: return "loamy sand"
    if (7 <= cl < 20 and sa > 52) or (cl < 7 and si < 50): return "sandy loam"
    if 7 <= cl < 27 and 28 <= si < 50 and sa <= 52: return "loam"
    if (si >= 50 and 12 <= cl < 27) or (50 <= si < 80 and cl < 12): return "silt loam"
    if si >= 80 and cl < 12: return "silt"
    if 20 <= cl < 35 and si < 28 and sa > 45: return "sandy clay loam"
    if 27 <= cl < 40 and 20 < sa <= 45: return "clay loam"
    if 27 <= cl < 40 and sa <= 20: return "silty clay loam"
    if cl >= 35 and sa > 45: return "sandy clay"
    if cl >= 40 and si >= 40: return "silty clay"
    return "clay"


def fetch(var, depth, box, out):
    if not os.path.exists(out):
        url = (f"https://maps.isric.org/mapserv?map=/map/{var}.map&SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage"
               f"&COVERAGEID={var}_{depth}_mean&FORMAT=image/tiff&SUBSET=long({box[0]},{box[1]})&SUBSET=lat({box[2]},{box[3]})"
               "&SUBSETTINGCRS=http://www.opengis.net/def/crs/EPSG/0/4326&OUTPUTCRS=http://www.opengis.net/def/crs/EPSG/0/4326")
        subprocess.run(["curl", "-s", "-m", "120", "-o", out, url], check=True)
    with rasterio.open(out) as r:
        return r.read(1).astype(float), r.transform, r.crs


dl = sys.argv[1]
for basin, box in BOX.items():
    with rasterio.open(f"{WF}/data/domain_{basin}/attributes/glaciers/domain_{basin}_domain_type.tif") as r:
        typ, tt, tc = r.read(1), r.transform, r.crs
    with rasterio.open(f"{WF}/data/domain_{basin}/attributes/glaciers/domain_{basin}_hru_id.tif") as r:
        hru = r.read(1)
    tex = {}
    for var in ("sand", "silt", "clay"):
        acc = np.zeros(typ.shape)
        for d, w in zip(DEPTHS, WEIGHT):
            a, at, ac = fetch(var, d, box, os.path.join(dl, f"{basin}_{var}_{d}.tif"))
            a[a <= 0] = np.nan
            g = np.full(typ.shape, np.nan)
            reproject(a, g, src_transform=at, src_crs=ac, dst_transform=tt, dst_crs=tc, src_nodata=np.nan, dst_nodata=np.nan,
                      resampling=Resampling.nearest)
            acc += g * w / sum(WEIGHT) / 10.0  # g/kg to %
        tex[var] = acc
    upland = (typ == 1) & (hru > 0)
    ok = upland & np.isfinite(tex["sand"])
    print(f"== {basin}: upland cells {upland.sum()}, with SoilGrids {ok.sum()}")
    for h in sorted(np.unique(hru[ok])):
        m = ok & (hru == h)
        sa, si, cl = (np.nanmean(tex[v][m]) for v in ("sand", "silt", "clay"))
        cls = usda(sa, si, cl)
        print(f"  HRU {h}: sand {sa:.0f}% silt {si:.0f}% clay {cl:.0f}% -> {cls}: theta_r, theta_s, alpha, n, Ks = {CP[cls]}")
    sa, si, cl = (np.nanmean(tex[v][ok]) for v in ("sand", "silt", "clay"))
    print(f"  basin upland: sand {sa:.0f}% silt {si:.0f}% clay {cl:.0f}% -> {usda(sa, si, cl)} {CP[usda(sa, si, cl)]}; "
          f"sand range over cells {np.nanpercentile(tex['sand'][ok], 5):.0f}-{np.nanpercentile(tex['sand'][ok], 95):.0f}%")
