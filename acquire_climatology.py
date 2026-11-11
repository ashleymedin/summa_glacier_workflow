#!/usr/bin/env python3
"""Clip the CHELSA V2.1 1981-2010 annual precipitation (bio12, 30 arcsec, 0.1 kg m-2 yr-1 per count) to a domain.

The window is the domain's raw ERA5 grid (forcing/raw_data) and half a degree around it, read from the global file
in place and written to the domain YAML's precip_climatology path, which remap_forcing.py scales the raw
precipitation of each HRU by.

    ./acquire_climatology.py domains/gulkana_general.yaml
"""

import argparse
import glob
import os

import rasterio
from netCDF4 import Dataset
from rasterio.windows import from_bounds

from domain_config import load_config

URL = "/vsicurl/https://os.zhdk.cloud.switch.ch/chelsav2/GLOBAL/climatologies/1981-2010/bio/CHELSA_bio12_1981-2010_V.2.1.tif"
MARGIN = 0.5  # deg beyond the ERA5 grid points


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/, with precip_climatology")
    a = p.parse_args()
    c = load_config(a.config)
    dom, project = c["domain"], c["project_dir"]
    raw = sorted(glob.glob(os.path.join(project, "forcing", "raw_data", f"domain_{dom}_ERA5_merged_*.nc")))
    if not raw:
        raise SystemExit("no raw ERA5 in forcing/raw_data; run acquire_era5.py first")
    with Dataset(raw[0]) as f:
        lat, lon = f["latitude"][:], f["longitude"][:]
    out = c["precip_climatology"]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with rasterio.open(URL) as r:
        w = from_bounds(lon.min() - MARGIN, lat.min() - MARGIN, lon.max() + MARGIN, lat.max() + MARGIN,
                        r.transform).round_offsets().round_lengths()
        data = r.read(1, window=w)
        prof = r.profile.copy()
        prof.update(width=data.shape[1], height=data.shape[0], transform=r.window_transform(w), nodata=65535,
                    tiled=True, blockxsize=256, blockysize=256)
    with rasterio.open(out, "w", **prof) as o:
        o.write(data, 1)
        o.scales, o.offsets = (0.1,), (0.0,)
    print(f"wrote {out} ({data.shape[0]} x {data.shape[1]})")


if __name__ == "__main__":
    main()
