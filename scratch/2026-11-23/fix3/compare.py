#!/usr/bin/env python3
"""Calibration-years objectives of each fix3 pair: the search's own value, the rerun as found (asis) and with the three fixed (fix3)."""
import glob
import os

import netCDF4 as nc4
import numpy as np

RUNS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "runs"))


def obj(path, s=None):
    with nc4.Dataset(glob.glob(path)[0]) as d:
        o = np.ma.filled(d["objective"][:].astype(float), np.nan)
    return o[s - 1] if s else o[0]


for p in sorted(glob.glob(f"{RUNS}/*/calibration*_rerun/sample_*_fix3")):
    case, rerun, smp = p.split("/")[-3:]
    name, s = rerun[:-len("_rerun")], int(smp.split("_")[1])
    search = obj(f"{RUNS}/{case}/{name}/output/*_calibration.nc", s)
    asis = obj(f"{p[:-5]}_asis/output/*_calibration.nc") if glob.glob(f"{p[:-5]}_asis/output/*_calibration.nc") else [np.nan] * 2
    if not glob.glob(f"{p}/output/*_calibration.nc"):
        continue
    fix = obj(f"{p}/output/*_calibration.nc")
    print(f"{case:18s} {name:20s} {s:4d}  search {search[0]:.3f} {search[1]:4.0f}  asis {asis[0]:.3f} {asis[1]:4.0f}  fix3 {fix[0]:.3f} {fix[1]:4.0f}")
