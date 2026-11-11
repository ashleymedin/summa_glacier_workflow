#!/usr/bin/env python3
"""Clip CHELSA V2.1 1981-2010 climatologies (30 arcsec) to a domain, for remap_forcing.py: the annual precipitation
(bio12) to the YAML's precip_climatology, and the twelve monthly mean wind speeds (sfcWind) as the bands of its
wind_climatology, each with its own scale and offset.

The window is the domain's raw ERA5 grid (forcing/raw_data) and half a degree around it, read from the global files
in place.

    ./acquire_climatology.py domains/gulkana_general.yaml
"""

import argparse
import glob
import os

import numpy as np
import rasterio
from netCDF4 import Dataset
from rasterio.windows import from_bounds

from domain_config import load_config

BASE = "/vsicurl/https://os.zhdk.cloud.switch.ch/chelsav2/GLOBAL/climatologies/1981-2010/"
PRECIP = BASE + "bio/CHELSA_bio12_1981-2010_V.2.1.tif"
WIND = BASE + "sfcWind/CHELSA_sfcWind_{m:02d}_1981-2010_V.2.1.tif"
MARGIN = 0.5  # deg beyond the ERA5 grid points


def clip(urls, out, bounds):
    """The window of each global file as one band of out, keeping each file's nodata, scale and offset."""
    bands, scales, offsets = [], [], []
    for url in urls:
        with rasterio.open(url) as r:
            w = from_bounds(*bounds, r.transform).round_offsets().round_lengths()
            bands.append(r.read(1, window=w))
            scales.append(r.scales[0]); offsets.append(r.offsets[0])
            prof = r.profile.copy()
            prof.update(width=bands[-1].shape[1], height=bands[-1].shape[0], transform=r.window_transform(w),
                        count=len(urls), nodata=r.nodata if r.nodata is not None else 65535,
                        tiled=True, blockxsize=256, blockysize=256)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with rasterio.open(out, "w", **prof) as o:
        o.write(np.stack(bands))
        o.scales, o.offsets = tuple(scales), tuple(offsets)
    print(f"wrote {out} ({len(urls)} band(s), {bands[0].shape[0]} x {bands[0].shape[1]})")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/, with precip_climatology and/or wind_climatology")
    a = p.parse_args()
    c = load_config(a.config)
    dom, project = c["domain"], c["project_dir"]
    raw = sorted(glob.glob(os.path.join(project, "forcing", "raw_data", f"domain_{dom}_ERA5_merged_*.nc")))
    if not raw:
        raise SystemExit("no raw ERA5 in forcing/raw_data; run acquire_era5.py first")
    with Dataset(raw[0]) as f:
        lat, lon = f["latitude"][:], f["longitude"][:]
    bounds = (lon.min() - MARGIN, lat.min() - MARGIN, lon.max() + MARGIN, lat.max() + MARGIN)
    if "precip_climatology" in c:
        clip([PRECIP], c["precip_climatology"], bounds)
    if "wind_climatology" in c:
        clip([WIND.format(m=m) for m in range(1, 13)], c["wind_climatology"], bounds)


if __name__ == "__main__":
    main()
