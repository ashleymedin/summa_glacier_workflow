#!/usr/bin/env python3
"""Copy each domain's vegTypeIndex and mHeight (upland_domain.py vegetation) into the built cases' attributes, by hruId,
so the tracked runs and tests match a rebuild; HRUs the domain lacks (a stream) keep theirs."""

import glob
import os

import netCDF4 as nc4
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")


def source(case):
    basin = "Wolverine" if "wolverine" in case else "Gulkana"
    return os.path.join(ROOT, "data", f"domain_{basin}{'_general' if 'general' in case else ''}", "settings", "SUMMA", "attributes_glac.nc")


for path in sorted(glob.glob(os.path.join(ROOT, "runs", "*", "summa_inputs", "attributes*.nc"))
                   + glob.glob(os.path.join(ROOT, "tests", "*", "summa_inputs", "attributes*.nc"))):
    case = path.split(os.sep)[-3]
    if "wolverine" not in case and "gulkana" not in case:
        continue
    with nc4.Dataset(source(case)) as s:
        veg = dict(zip(np.asarray(s["hruId"][:]).astype(int), np.asarray(s["vegTypeIndex"][:])))
        mh = dict(zip(np.asarray(s["hruId"][:]).astype(int), np.asarray(s["mHeight"][:])))
    with nc4.Dataset(path, "a") as d:
        ids = np.asarray(d["hruId"][:]).astype(int)
        old = list(np.asarray(d["vegTypeIndex"][:]))
        d["vegTypeIndex"][:] = [veg.get(h, v) for h, v in zip(ids, old)]
        d["mHeight"][:] = [mh.get(h, m) for h, m in zip(ids, np.asarray(d["mHeight"][:]))]
        print(f"{os.path.relpath(path, ROOT)}: vegTypeIndex {[int(v) for v in old]} -> {[int(v) for v in d['vegTypeIndex'][:]]}")
