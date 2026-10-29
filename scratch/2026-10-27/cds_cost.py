#!/usr/bin/env python3
"""Submit surface and model-level requests of growing size, report which the CDS accepts, and cancel them."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import cdsapi
from ecmwf.datastores import Client
import acquire_era5 as a
from domain_config import load_config

c = load_config("domains/gulkana.yaml")
area = a.grid_area(c["project_dir"], c["domain"], os.path.join(c["project_dir"], "forcing", "raw_data"))
u, k, _ = cdsapi.api.get_url_key_verify(None, None, None)
cl = Client(url=u, key=k)
for n in (12, 6, 4, 3, 2, 1):
    ms = list(range(1, n + 1))
    for name, coll, req in (("sfc", "reanalysis-era5-single-levels", a.sfc_request(2006, ms, area)),
                            ("ml", "reanalysis-era5-complete", a.ml_request(2006, ms, area, "1"))):
        try:
            r = cl.submit(coll, req)
            print(n, name, "accepted", flush=True)
            r.delete()
        except Exception as e:
            print(n, name, "refused:", str(e).splitlines()[-1][:80], flush=True)
