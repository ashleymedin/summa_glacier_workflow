#!/usr/bin/env python3
"""Fetch ITS_LIVE annual surface velocity (v02, 120 m mosaics) onto a domain's largest glacier's flow grid.

Each year's speed v (m yr-1), its error and the count of velocity pairs behind it are taken, nearest neighbour, onto the
UTM grid the flow model holds for the largest glacier of the domain (nx, ny and gridId of settings/SUMMA/attributes_glac.nc).
Writes observations/storage/velocity/itslive_annual.npz: years, transform (the grid's affine), and v, v_error, count of
shape (year, ny, nx), NaN where the mosaic has no value.  Years the archive does not hold yet are left out.

    ./acquire_velocity.py domains/gulkana.yaml --first 2004
"""

import argparse
import os

import netCDF4 as nc4
import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject

from domain_config import load_config
from glacier_cold_state import grid_transforms

URL = "/vsicurl/https://its-live-data.s3.amazonaws.com/velocity_mosaic/v2/annual/cog/ITS_LIVE_velocity_120m_RGI01A_{y}_v02_{f}.tif"
FIELDS = ("v", "v_error", "count")


def available(year):
    try:
        with rasterio.open(URL.format(y=year, f="v")):
            return True
    except rasterio.errors.RasterioIOError:
        return False


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    p.add_argument("--first", type=int, default=2004, help="first year")
    p.add_argument("--last", type=int, default=2030, help="last year tried; later years the archive lacks are skipped")
    a = p.parse_args()
    os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")

    c = load_config(a.config)
    project = c["project_dir"]
    transforms, crs = grid_transforms(project, c["domain"], c["utm_epsg"])
    with nc4.Dataset(os.path.join(project, "settings", "SUMMA", "attributes_glac.nc")) as d:
        nx, ny, ids = (np.asarray(d[v][:, 0]).astype(int) for v in ("nx", "ny", "gridId"))
    g = int(np.argmax(nx * ny))
    transform = transforms[int(ids[g])]
    years = [y for y in range(a.first, a.last + 1) if available(y)]
    out = {f: np.full((len(years), ny[g], nx[g]), np.nan, np.float32) for f in FIELDS}
    for i, y in enumerate(years):
        for f in FIELDS:
            with rasterio.open(URL.format(y=y, f=f)) as src:
                reproject(rasterio.band(src, 1), out[f][i], dst_transform=transform, dst_crs=crs, dst_nodata=np.nan,
                          resampling=Resampling.nearest, src_nodata=src.nodata)
        print(y, f"median speed {np.nanmedian(out['v'][i]):.1f} m/yr, {np.isfinite(out['v'][i]).mean():.0%} of cells", flush=True)
    folder = os.path.join(project, "observations", "storage", "velocity")
    os.makedirs(folder, exist_ok=True)
    np.savez_compressed(os.path.join(folder, "itslive_annual.npz"), years=np.array(years), transform=np.array(transform)[:6], **out)
    print("wrote", folder)


if __name__ == "__main__":
    main()
