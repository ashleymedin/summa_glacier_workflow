#!/usr/bin/env python3
"""SoilGrids 2.0 coarse-fragment volume (cfvo, % of soil volume, 0-60 cm) and bulk density over each basin's upland, by HRU,
with the ESA WorldCover class mix of the same cells.

    soilgrids_cfvo.py <download dir>
"""
import os
import subprocess
import sys

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

WF = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
BOX = {"Gulkana": (-145.55, -145.33, 63.21, 63.33), "Wolverine": (-148.98, -148.84, 60.36, 60.45)}
DEPTHS = ["0-5cm", "5-15cm", "15-30cm", "30-60cm"]
WEIGHT = [5, 10, 15, 30]

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
    val = {}
    for var, scale in (("cfvo", 10.0), ("bdod", 100.0)):  # cfvo cm3/dm3 to %, bdod cg/cm3 to g/cm3
        acc = np.zeros(typ.shape)
        for d, w in zip(DEPTHS, WEIGHT):
            a, at, ac = fetch(var, d, box, os.path.join(dl, f"{basin}_{var}_{d}.tif"))
            a[a <= 0] = np.nan  # SoilGrids leaves unmapped (rock, ice) cells at 0
            g = np.full(typ.shape, np.nan)
            reproject(a, g, src_transform=at, src_crs=ac, dst_transform=tt, dst_crs=tc, src_nodata=np.nan, dst_nodata=np.nan,
                      resampling=Resampling.nearest)
            acc += g * w / sum(WEIGHT) / scale
        val[var] = acc
    up = (typ == 1) & (hru > 0)
    ok = up & np.isfinite(val["cfvo"])
    print(f"== {basin}: upland cells {up.sum()}, mapped by SoilGrids {ok.sum()} ({100 * ok.sum() / up.sum():.0f}%)")
    for h in sorted(np.unique(hru[ok])):
        m = ok & (hru == h)
        c = val["cfvo"][m]
        print(f"  HRU {h}: cfvo mean {np.nanmean(c):.0f}% (5-95% {np.nanpercentile(c, 5):.0f}-{np.nanpercentile(c, 95):.0f}), "
              f"bulk density {np.nanmean(val['bdod'][m]):.2f} g/cm3")
    print(f"  basin upland cfvo {np.nanmean(val['cfvo'][ok]):.0f}%")
