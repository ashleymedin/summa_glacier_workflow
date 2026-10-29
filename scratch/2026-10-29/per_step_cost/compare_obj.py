#!/usr/bin/env python3
"""Compare the objectives of tolall runs trial by trial against a reference run.
usage: compare_obj.py ref_tag tag [tag ...]   (tolall_<tag>/output/*_calibration.nc)"""
import sys, glob, numpy as np, netCDF4 as nc
def load(tag):
    d = nc.Dataset(glob.glob(f"tolall_{tag}/output/*_calibration.nc")[0])
    names = ["".join(c.decode() for c in r if c).strip() for r in d["target_name"][:]]
    return names, np.array(d["objective"][:]), np.array(d["trial_failed"][:])
names, ref, _ = load(sys.argv[1])
print("targets", names)
for tag in sys.argv[2:]:
    _, o, f = load(tag)
    d = np.abs(o - ref)
    print(f"{tag}: failed {int(f.sum())}, identical {np.array_equal(o, ref)}, max |diff| per target", " ".join(f"{x:.3g}" for x in d.max(0)))
