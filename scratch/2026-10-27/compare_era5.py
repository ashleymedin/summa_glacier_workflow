#!/usr/bin/env python3
"""Compare a CDS month in scratch/2026-10-27/verify with the existing raw_data month."""
import glob, os, sys
import numpy as np, xarray as xr
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from domain_config import load_config
c = load_config("domains/gulkana.yaml")
new_p = glob.glob(os.path.join(os.path.dirname(__file__), "verify", "*.nc"))[0]
new, old = xr.open_dataset(new_p), xr.open_dataset(os.path.join(c["project_dir"], "forcing", "raw_data", os.path.basename(new_p)))
print("time equal:", np.array_equal(new.time, old.time), new.time.values[:2], old.time.values[:2])
print("grid equal:", np.array_equal(new.latitude, old.latitude), np.array_equal(new.longitude, old.longitude))
for v in old.data_vars:
    d = new[v].values.astype("f8") - old[v].values.astype("f8")
    print(f"{v:9s} max|diff| {abs(d).max():.3g}  rms {np.sqrt((d**2).mean()):.3g}  old range {float(old[v].min()):.4g}..{float(old[v].max()):.4g}")
    k = 1
    d1 = new[v].values[k:].astype("f8") - old[v].values[:-k].astype("f8")
    print(f"          shifted by one hour: max|diff| {abs(d1).max():.3g}")
