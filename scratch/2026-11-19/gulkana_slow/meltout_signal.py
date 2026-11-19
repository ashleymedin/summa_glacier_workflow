#!/usr/bin/env python3
"""ArcticDEM strip trends on Gulkana's lower glacier (general grid): cells whose ice the added setup's later survey outline says
melted out (its bed raised over 20 m above the general bed) against the cells still ice, to find a strip-only melt-out signal."""
import glob
import os
import sys

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

WF = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, WF)
from glacier_rasters import height_trend, strip_heights  # noqa: E402

G, A = f"{WF}/data/domain_Gulkana_general/attributes/", f"{WF}/data/domain_Gulkana/attributes/"
src = rasterio.open(G + "elevation/dem/domain_Gulkana_elv.tif")


def onto(path):
    out = np.full((src.height, src.width), np.nan)
    with rasterio.open(path) as r:
        reproject(rasterio.band(r, 1), out, src_transform=r.transform, src_crs=r.crs, dst_transform=src.transform,
                  dst_crs=src.crs, resampling=Resampling.nearest, src_nodata=r.nodata, dst_nodata=np.nan)
    return out


dem = src.read(1).astype(float)
surf, bed = onto(G + "elevation/dem/domain_Gulkana_glacier_elv.tif"), onto(G + "elevation/dem/domain_Gulkana_bedrock_elv.tif")
abed = onto(A + "elevation/dem/domain_Gulkana_bedrock_elv.tif")
typ = onto(G + "glaciers/domain_Gulkana_domain_type.tif")
glacier = (typ >= 2) & (typ <= 4)
years, h = strip_heights(dem, glacier, src, sorted(glob.glob(f"{WF}/data/external/GlacierDEM/ArcticDEM_Gulkana_series/*.tif")))
early, late = height_trend(years[years < 2018], h[years < 2018], 2011.0, 3), height_trend(years, h, 2018.0, 3)
with np.errstate(all="ignore"):
    recent = np.nanmedian(h[years >= 2020], axis=0)
low = glacier & (surf < 1500)
lost = low & (abed - bed > 20)
kept = low & ~lost
for name, m in (("lost (added)", lost), ("kept", kept)):
    print(f"{name:13s} n {m.sum():4d}  slope 2011-17 {np.nanpercentile(early[m], [25, 50, 75]).round(2)}  2018-21 "
          f"{np.nanpercentile(late[m], [25, 50, 75]).round(2)}  2020-21 below start {np.nanpercentile((surf - recent)[m], [25, 50, 75]).round(1)}"
          f"  added thickness {np.nanmedian((surf - abed)[m]):.0f} m")
for thr in (0.5, 1.0):
    flag = low & (late > -thr) & (early < -1.0)
    print(f"late > -{thr}, early < -1: flags {(flag & lost).sum()} lost, {(flag & kept).sum()} kept")
np.savez(os.path.join(os.path.dirname(os.path.abspath(__file__)), "meltout_signal.npz"), early=early, late=late, lost=lost, kept=kept)
