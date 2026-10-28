#!/usr/bin/env python3
"""Seed a domain's project folder from another domain's, for the general setup of the same basin.

The general setup of a glacier basin (global data only) has its own project folder, built by setup_glacier_domain.py, but starts
from the pieces the SYMFLUENCE domain holds that do not depend on the glacier data: the HRU and catchment shapefiles, the land and
soil classes, the MERIT surface DEM, the SUMMA settings, and the ERA5 forcing, which is linked, not copied. The domain YAML's
seed_from names the source project folder.

    ./seed_domain.py domains/gulkana_general.yaml
"""

import argparse
import os
import shutil

from domain_config import load_config

HERE = os.path.dirname(os.path.abspath(__file__))
COPY = ("shapefiles", "attributes/landclass", "attributes/soilclass", "attributes/radiation", "settings")
GENERATED = ("attributes_glac.nc", "coldstate_glac.nc")  # written by the setup steps
LINK = ("forcing/raw_data", "forcing/SUMMA_input")


def seed(src, dst, domain):
    for rel in COPY:
        if os.path.isdir(os.path.join(src, rel)):
            shutil.copytree(os.path.join(src, rel), os.path.join(dst, rel), dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns(*GENERATED, ".DS_Store"))
    dem = os.path.join("attributes", "elevation", "dem", f"domain_{domain}_elv.tif")
    os.makedirs(os.path.join(dst, os.path.dirname(dem)), exist_ok=True)
    shutil.copy2(os.path.join(src, dem), os.path.join(dst, dem))
    for rel in LINK:
        target = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if not os.path.lexists(target):
            os.symlink(os.path.abspath(os.path.join(src, rel)), target)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/ with a seed_from")
    a = p.parse_args()
    c = load_config(a.config)
    if not c.get("seed_from"):
        raise SystemExit(f"{a.config} has no seed_from")
    src = os.path.abspath(os.path.join(HERE, c["seed_from"]))
    seed(src, c["project_dir"], c["domain"])
    print(f"seeded {c['project_dir']} from {src}")


if __name__ == "__main__":
    main()
