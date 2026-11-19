#!/usr/bin/env python3
"""Test cases onto Shaw et al.'s glacier air cooling and the 1 mm firn viscosity, parameters only: glacierTempReduction and
firnViscosity in localParamInfo.txt, and glacierTempReduction by HRU in trialParams.nc (each GRU's glacier's k).

    tests_cooling_firn.py <settings dir>:<RGI id of GRU 1>[,<RGI id of GRU 2>...] [...]
"""
import os
import re
import sys

import netCDF4 as nc4
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
from build_cases import FIRN_VISCOSITY  # noqa: E402
from shaw_cooling import shaw_k  # noqa: E402


def set_line(path, name, value, lo, hi):
    text = open(path).read()
    line = f"{name:<26s}| {value:12.4e} | {lo:12.4e} | {hi:12.4e}"
    text, n = re.subn(rf"^{name}\s*\|.*$", line, text, flags=re.M)
    open(path, "w").write(text if n else text.rstrip("\n") + "\n" + line + "\n")


for spec in sys.argv[1:]:
    d, ids = spec.split(":")
    k = [shaw_k(i) for i in ids.split(",")]
    with nc4.Dataset(os.path.join(d, "attributes.nc")) as a:
        gru = np.asarray(a["hru2gruId"][:])
    by_hru = np.array([k[g - 1] for g in gru])
    set_line(os.path.join(d, "localParamInfo.txt"), "glacierTempReduction", float(np.median(by_hru)), 0.0, 1.0)
    set_line(os.path.join(d, "localParamInfo.txt"), "firnViscosity", FIRN_VISCOSITY, 1.0e12, 1.0e14)
    with nc4.Dataset(os.path.join(d, "trialParams.nc"), "a") as t:
        v = t["glacierTempReduction"] if "glacierTempReduction" in t.variables else t.createVariable("glacierTempReduction", "f8", ("hru",))
        v[:] = by_hru
    print(d, "glacierTempReduction by HRU", np.round(by_hru, 3), f"firnViscosity {FIRN_VISCOSITY:.3g}")
