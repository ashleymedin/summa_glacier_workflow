#!/usr/bin/env python3
"""Move a raw-ERA5 case's glacier snowfall from one gradient to another in place: precipElevGrad in localParamInfo.txt, and
the glacier frozenPrecipMultip of trialParams.nc times exp((new - old)(z_hru - z_gru)), z_gru the glacier-area-weighted mean
HRU elevation of the HRU's GRU, as build_cases.glacier_snow_shape builds it.

    regrade_shape.py 0.0017 0.002 tests/gulkana/summa_inputs [...]
"""
import os
import re
import sys

import netCDF4 as nc4
import numpy as np

GLACIER = (2, 3, 4)
old, new = float(sys.argv[1]), float(sys.argv[2])
for inputs in sys.argv[3:]:
    with nc4.Dataset(os.path.join(inputs, "coldState.nc")) as c:
        shape = c["domType"].shape[-2:]
        types = np.asarray(c["domType"][:]).reshape(shape).T
        area = np.ma.filled(np.asarray(c["DOMarea"][:]).reshape(shape).T, 0.0)
    with nc4.Dataset(os.path.join(inputs, "attributes.nc")) as a:
        z = np.asarray(a["elevation"][:], float)
        gru = np.asarray(a["hru2gruId"][:])
    glacier = np.isin(types, GLACIER)
    ice = np.where(glacier, np.maximum(area, 0.0), 0.0).sum(axis=0)
    scale = np.ones(len(z))
    for g in np.unique(gru):
        m = gru == g
        if ice[m].sum() > 0:
            scale[m] = np.exp((new - old) * (z[m] - np.sum(z[m] * ice[m]) / ice[m].sum()))
    with nc4.Dataset(os.path.join(inputs, "trialParams.nc"), "a") as t:
        v = t["frozenPrecipMultip"]
        v[:] = np.where(glacier, v[:] * scale[None, :], v[:])
    p = os.path.join(inputs, "localParamInfo.txt")
    text = open(p).read()
    text = re.sub(r"^(precipElevGrad\s*\|\s*)[\d.eE+-]+", lambda m: f"{m.group(1)}{new:.6f}", text, flags=re.M)
    open(p, "w").write(text)
    print(inputs, "scale", np.round(scale, 3))
