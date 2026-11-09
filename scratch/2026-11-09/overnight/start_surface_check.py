#!/usr/bin/env python3
"""The general setup's start surface (Copernicus GLO-30 carried at Hugonnet's rates) and MERIT against the added setup's
(the USGS survey carried to the start), on the cells that are glacier in both: median offset and scatter (std), m.

    ./start_surface_check.py
"""
import os

import numpy as np
import rasterio

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "data")


def grid(domain, basin, name):
    with rasterio.open(os.path.join(DATA, f"domain_{domain}", "attributes", "elevation", "dem", f"domain_{basin}_{name}.tif")) as r:
        x = r.read(1).astype(float)
        x[x == r.nodata] = np.nan
    return x


for basin in ("Wolverine", "Gulkana"):
    out = {}
    for proj in ("_utm", ""):
        add_s, add_b = grid(basin, basin, "glacier_elv" + proj), grid(basin, basin, "bedrock_elv" + proj)
        gen_s, gen_b = grid(basin + "_general", basin, "glacier_elv" + proj), grid(basin + "_general", basin, "bedrock_elv" + proj)
        ice = (add_s - add_b > 0.1) & (gen_s - gen_b > 0.1)
        rows = [("Copernicus carried", gen_s)] + ([("MERIT", grid(basin, basin, "elv"))] if proj == "" else [])
        for label, s in rows:
            d = (s - add_s)[ice & np.isfinite(s)]
            print(f"{basin:9s} {label:18s} grid{proj or '_geo':5s} cells {d.size:5d}  median {np.median(d):+6.1f} m  std {np.std(d):5.1f} m")
