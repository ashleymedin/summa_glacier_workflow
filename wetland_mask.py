#!/usr/bin/env python3
"""Write a wetlandMask grid into a case's attributes.nc: the lowest valid-bed cells of the wetland's HRU inside a
domain's lake box, as many as make up the lake's largest area, so SUMMA opens the wetland as the glacier leaves them.

    ./wetland_mask.py ATTRIBUTES DOMAIN_YAML MAX_AREA_M2 HRU_ID [--box N]     N indexes observations.lake_area (default 0)
"""

import argparse
import os
import sys

import netCDF4 as nc4
import numpy as np
from pyproj import Transformer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from domain_config import load_config  # noqa: E402
from glacier_cold_state import grid_transforms  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("attributes")
    ap.add_argument("domain")
    ap.add_argument("max_area", type=float)
    ap.add_argument("hru", type=int, help="hruId of the wetland's HRU")
    ap.add_argument("--box", type=int, default=0)
    a = ap.parse_args()
    c = load_config(a.domain)
    tr, crs = grid_transforms(c["project_dir"], c["domain"], c["utm_epsg"])
    ll = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    box = c["observations"]["lake_area"][a.box]["box"]
    with nc4.Dataset(a.attributes, "a") as at:
        if "wetlandMask" not in at.variables:
            at.createVariable("wetlandMask", "f8", at["bed_elev"].dimensions, fill_value=0.0)
            at["wetlandMask"].long_name = "binary mask of cells a wetland can fill once free of ice"
        mask = np.zeros(at["bed_elev"].shape)
        for g in range(at.dimensions["grid"].size):
            gid, ny, nx, dx, dy = (int(at["gridId"][g, 0]), int(at["ny"][g, 0]), int(at["nx"][g, 0]),
                                   float(at["dx"][g, 0]), float(at["dy"][g, 0]))
            bed = np.ma.filled(at["bed_elev"][:ny, :nx, g, 0].astype(float), np.nan)
            jj, ii = np.mgrid[0:ny, 0:nx]
            lon, lat = ll.transform(*(tr[gid] * (ii + 0.5, jj + 0.5)))
            inbox = (lon >= box[0]) & (lon <= box[2]) & (lat >= box[1]) & (lat <= box[3]) & np.isfinite(bed) \
                & (np.ma.filled(at["cell2hruId"][:ny, :nx, g, 0], -1) == a.hru)
            n = min(int(round(a.max_area/(dx*dy))), int(inbox.sum()))
            if n == 0:
                continue
            pick = np.argsort(np.where(inbox, bed, np.inf), axis=None)[:n]
            m = np.zeros(bed.size); m[pick] = 1.0
            mask[:ny, :nx, g, 0] = m.reshape(bed.shape)
            print(f"grid {gid}: {n} cells, {n*dx*dy:.0f} m2, bed {np.sort(bed.ravel()[pick])[[0, -1]].round()} m")
        at["wetlandMask"][:] = mask
    if not mask.any():
        raise SystemExit(f"{a.attributes}: no cell of HRU {a.hru} with a bed inside the lake box")


if __name__ == "__main__":
    main()
