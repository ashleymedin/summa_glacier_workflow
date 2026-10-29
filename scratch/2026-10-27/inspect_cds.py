#!/usr/bin/env python3
"""Fetch 2008-01 from the CDS and print what the surface and model-level files hold."""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import cdsapi, xarray as xr
from ecmwf.datastores import Client
import acquire_era5 as a
from domain_config import load_config

c = load_config("domains/gulkana.yaml")
area = a.grid_area(c["project_dir"], c["domain"], os.path.join(c["project_dir"], "forcing", "raw_data"))
u, k, _ = cdsapi.api.get_url_key_verify(None, None, None)
cl = Client(url=u, key=k)
w = tempfile.mkdtemp(dir=os.path.dirname(__file__))
s = cl.submit("reanalysis-era5-single-levels", a.sfc_request(2008, [1], area)).download(w + "/sfc.download")
m = cl.submit("reanalysis-era5-complete", a.ml_request(2008, [1], area, "1")).download(w + "/ml.download")
for p in (s, m):
    for f in a.unpack(p, w + "/x" + os.path.basename(p)):
        d = xr.open_dataset(f)
        print(f, "\n", d, "\n", {v: int(d[v].isnull().sum()) for v in d.data_vars})
print(w)
