#!/usr/bin/env python3
"""Where the slowed melt-out criterion falls on a general domain: elevation, distance to the start margin and Millan thickness of
the flagged cells, from the scratch rasters of glacier_rasters.py --output-dir and the domain's own (unchanged) ones.

    slowed_cells.py Gulkana scratch/2026-11-19/gulkana_slow/rasters_gulkana
"""
import glob
import os
import sys

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

WF = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, WF)
from glacier_rasters import cell_size, height_trend, strip_heights  # noqa: E402

name, new = sys.argv[1], sys.argv[2]
d = f"{WF}/data/domain_{name}_general/attributes/elevation/dem/domain_{name}_"
src = rasterio.open(d + "elv.tif")
dem = src.read(1).astype(float)
surf, bed = rasterio.open(d + "glacier_elv.tif").read(1), rasterio.open(d + "bedrock_elv.tif").read(1)
nbed = rasterio.open(f"{new}/domain_{name}_bedrock_elv.tif").read(1)
typ = rasterio.open(f"{WF}/data/domain_{name}_general/attributes/glaciers/domain_{name}_domain_type.tif").read(1)
glacier = (typ >= 2) & (typ <= 4)
years, h = strip_heights(dem, glacier, src, sorted(glob.glob(f"{WF}/data/external/GlacierDEM/ArcticDEM_{name}_series/*.tif")))
early, late = height_trend(years[years < 2018], h[years < 2018], 2011.0, 3), height_trend(years, h, 2018.0, 3)
flag = glacier & (early < -1) & (late > -0.5)
dx, dy = cell_size(src, dem.shape)
edge = distance_transform_edt(glacier, sampling=(dy, dx))
for lo, hi in ((0, 1300), (1300, 1600), (1600, 2000), (2000, 3000)):
    m = flag & (surf >= lo) & (surf < hi)
    if m.any():
        print(f"{lo}-{hi} m: {m.sum()} cells, margin distance median {np.median(edge[m]):.0f} m, thickness {np.median((surf - bed)[m]):.0f} m, "
              f"bed raised {np.median((nbed - bed)[m]):.0f} m, early {np.median(early[m]):.1f} late {np.median(late[m]):.1f} m/yr, strips since 2018 {np.median(np.isfinite(h[years >= 2018][:, m]).sum(0)):.0f}")
print("glacier cells by band:", {f"{lo}": int((glacier & (surf >= lo) & (surf < lo + 300)).sum()) for lo in range(0, 2700, 300)})

from scipy.ndimage import binary_dilation, label  # noqa: E402
abl = (typ == 3) | (typ == 4)
f = flag & abl
lab, n = label(f)
touch = np.unique(lab[f & binary_dilation(~glacier, iterations=1)])
f = np.isin(lab, touch[touch > 0])
print(f"ablation zone, connected to the margin: {f.sum()} cells")
for lo, hi in ((0, 1300), (1300, 1600), (1600, 2000), (2000, 3000)):
    m = f & (surf >= lo) & (surf < hi)
    if m.any():
        print(f"  {lo}-{hi} m: {m.sum()} cells, margin distance median {np.median(edge[m]):.0f} m, thickness {np.median((surf - bed)[m]):.0f} m")
np.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"slowed_{name}.npy"), f)
