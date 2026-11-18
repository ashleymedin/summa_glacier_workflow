#!/usr/bin/env python3
"""Copy of a case's summa_inputs whose glacier domains take glacierTempReduction by HRU (trialParams.nc), to test warm valley air
that reaches the lowest ice uncooled and cools as it climbs; with --upland, the upland domains' frozenPrecipMultip set instead.

    valley_air_inputs.py wolverine_added <out> --cooling 1.0 0.79 0.65
    valley_air_inputs.py gulkana_added <out> --upland 1.5
"""
import argparse
import os
import shutil

import netCDF4 as nc
import numpy as np

RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "runs")
p = argparse.ArgumentParser()
p.add_argument("case")
p.add_argument("out")
p.add_argument("--cooling", type=float, nargs="+", help="glacierTempReduction of each HRU's glacier domains")
p.add_argument("--upland", type=float, help="frozenPrecipMultip of the upland domains (types 1 and 3)")
a = p.parse_args()
if os.path.exists(a.out):
    shutil.rmtree(a.out)
shutil.copytree(f"{RUNS}/{a.case}/summa_inputs", a.out)
with nc.Dataset(f"{a.out}/coldState.nc") as c:
    typ = np.ma.filled(c["domType"][:], -1).T  # (dom, hru)
with nc.Dataset(f"{a.out}/trialParams.nc", "a") as d:
    if a.cooling:
        v = d.createVariable("glacierTempReduction", "f8", ("dom", "hru"))
        x = np.full(typ.shape, 1.0)
        for h, f in enumerate(a.cooling):
            x[np.isin(typ[:, h], (2, 4)), h] = f
        v[:] = x
        print("glacierTempReduction (dom, hru):", x.round(3).tolist())
    if a.upland is not None:
        x = np.array(d["frozenPrecipMultip"][:])
        x[(typ == 1) | (typ == 3)] = a.upland
        d["frozenPrecipMultip"][:] = x
        print("frozenPrecipMultip (dom, hru):", x.round(3).tolist())
