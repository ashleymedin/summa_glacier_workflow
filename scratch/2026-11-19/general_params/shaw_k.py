#!/usr/bin/env python3
"""Shaw et al. (2025) historical decoupling factor k and its predictors for the glaciers named, from
data/external/Shaw25CoolingFactor/HISTORICAL_DECOUPLING_ESTIMATES_DATABASE.mat.

    shaw_k.py RGI60-01.09162 RGI60-01.00570
"""
import os
import sys

import h5py
import numpy as np

WF = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
f = h5py.File(f"{WF}/data/external/Shaw25CoolingFactor/HISTORICAL_DECOUPLING_ESTIMATES_DATABASE.mat")
g = f["HISTORICAL_K"]
ids = ["".join(chr(c) for c in np.ravel(f[r][()])) for r in np.ravel(g["RGI_ID"][()])]
cols = ["K", "K_CI", "COOL", "COOL_CI", "TA", "Q", "FF", "LEN", "ELE", "DEB", "LAT", "LON"]
data = {c: np.ravel(g[c][()]) for c in cols}
k = data["K"]
print(f"all glaciers: k median {np.nanmedian(k):.2f}, 5-95% {np.nanpercentile(k, 5):.2f}-{np.nanpercentile(k, 95):.2f}")
a = data["REGION"] if "REGION" in data else np.ravel(g["REGION"][()])
print(f"region 1 (Alaska): k median {np.nanmedian(k[a == 1]):.2f}")
for want in sys.argv[1:]:
    i = ids.index(want) if want in ids else None
    print(want, "not found" if i is None else "  ".join(f"{c} {data[c][i]:.3g}" for c in cols))
