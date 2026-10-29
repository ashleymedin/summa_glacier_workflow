#!/usr/bin/env python3
"""Fetch 2008-01 from the CDS and compare it with the existing raw_data month (time stamps and values)."""
import os, sys, tempfile
import numpy as np
import xarray as xr
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import cdsapi
from acquire_era5 import fetch, write, grid_area
from domain_config import load_config

c = load_config("domains/gulkana.yaml")
dom, project = c["domain"], c["project_dir"]
raw = os.path.join(project, "forcing", "raw_data")
area = grid_area(project, dom, raw)
out = os.path.join(os.path.dirname(__file__), f"{dom}_200801_cds.nc")
with tempfile.TemporaryDirectory() as w:
    write(fetch(cdsapi.Client(), 2008, 1, area, w), out)
new, old = xr.open_dataset(out), xr.open_dataset(os.path.join(raw, f"domain_{dom}_ERA5_merged_200801.nc"))
print("time equal:", np.array_equal(new.time, old.time), new.time.values[:2], old.time.values[:2])
print("grid equal:", np.array_equal(new.latitude, old.latitude), np.array_equal(new.longitude, old.longitude))
for v in old.data_vars:
    d = new[v].values.astype("f8") - old[v].values.astype("f8")
    print(f"{v:9s} max|diff| {abs(d).max():.3g}  rms {np.sqrt((d**2).mean()):.3g}  old range {float(old[v].min()):.4g}..{float(old[v].max()):.4g}")
