#!/usr/bin/env python3
"""Hugonnet et al. (2021) glacier thinning, 2000-2020, averaged over each HRU's RGI 6 glacier cells.

The dh/dt tiles (100 m, UTM) are resampled bilinearly onto the domain's HRU-id grid; a cell counts where the RGI-id
raster marks glacier. Written as <domain>_hugonnet_hru.csv beside this script: hruId, glacier area (km2), mean
dh/dt (m/yr), and the mass rate at Hugonnet's 850 kg m-3 (m w.e./yr).

    hugonnet_by_hru.py Wolverine_general Wolverine
"""
import csv
import glob
import os
import sys

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

HERE = os.path.dirname(os.path.abspath(__file__))
G = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TILES = os.path.join(G, "data/external/Hugonnet/01_02_rgi60_2000-01-01_2020-01-01/dhdt")
RHO = 0.85  # Hugonnet et al. (2021) volume-to-mass conversion, w.e. per m of ice-and-firn


def by_hru(domain_dir, name):
    gdir = os.path.join(G, "data", f"domain_{domain_dir}", "attributes", "glaciers")
    with rasterio.open(os.path.join(gdir, f"domain_{name}_hru_id.tif")) as h:
        hru = h.read(1)
        tr, crs, shape = h.transform, h.crs, h.shape
        lat = tr.f + tr.e * np.arange(shape[0])[:, None] + tr.e / 2
    with rasterio.open(os.path.join(gdir, f"domain_{name}_rgi_id.tif")) as r:
        ice = r.read(1) > 0
    dhdt = np.full(shape, np.nan, np.float32)
    for t in sorted(glob.glob(os.path.join(TILES, "*_dhdt.tif"))):
        with rasterio.open(t) as s:
            out = np.full(shape, np.nan, np.float32)
            reproject(rasterio.band(s, 1), out, src_nodata=s.nodata, dst_transform=tr, dst_crs=crs, dst_nodata=np.nan,
                      resampling=Resampling.bilinear)
        dhdt = np.where(np.isfinite(out) & ~np.isfinite(dhdt), out, dhdt)
    # cell area on the geographic grid, km2
    area = (abs(tr.a) * 111.32 * np.cos(np.radians(lat))) * (abs(tr.e) * 110.57) * np.ones(shape)
    rows = []
    for k in sorted(int(x) for x in np.unique(hru) if x > 0):
        m = (hru == k) & ice & np.isfinite(dhdt)
        if not m.any():
            continue
        w = area[m]
        rate = float(np.sum(dhdt[m] * w) / w.sum())
        cover = float(((hru == k) & ice).sum())
        rows.append((k, round(float(w.sum()), 3), round(rate, 3), round(rate * RHO, 3), round(m.sum() / cover, 3)))
    return rows


def main():
    domain_dir, name = sys.argv[1:3]
    rows = by_hru(domain_dir, name)
    path = os.path.join(HERE, f"{domain_dir}_hugonnet_hru.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hruId", "glacier_km2", "dhdt_m_yr", "mb_mwe_yr", "covered_fraction"])
        w.writerows(rows)
    for r in rows:
        print(f"HRU {r[0]}: {r[1]:6.2f} km2  dh/dt {r[2]:+.2f} m/yr  {r[3]:+.2f} m w.e./yr  (covered {r[4]:.2f})")
    print(path)


if __name__ == "__main__":
    main()
