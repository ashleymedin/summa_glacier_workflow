#!/usr/bin/env python3
"""Run the glacier setup of a domain in data/, step by step, from its domain YAML.

Steps, in order (--steps picks some; the default is all of them):

  rasters   glacier_rasters.py: domain type, RGI id, debris thickness and bed rasters
  extend    glacier_extend.py: basin on the bed, glacier-capable cells downstream (needs pysheds)
            -- then, in SYMFLUENCE: elevation-band HRUs, forcing remapping, upland attributes.nc and coldState.nc --
  hrus      hru_attributes.py: HRU area, centre, elevation, slope and contour length from the polygons and DEM
  zonal     glacier_zonal_stats.py: per-HRU debris, domain-type, elevation, slope and aspect statistics
  forcing   spechum_ratio_from_campaign.py (if the YAML names a campaign) and correct_forcing_to_station.py:
            forcing/SUMMA_input/station_corrected
  coldstate glacier_cold_state.py: attributes_glac.nc and coldstate_glac.nc, started from cold_start

The tests and runs are then built from the domains by build_cases.py.

    ./setup_glacier_domain.py domains/wolverine.yaml --steps zonal coldstate
"""

import argparse
import os
import subprocess
import sys

from domain_config import load_config

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = ("rasters", "extend", "hrus", "zonal", "forcing", "coldstate")


def run(*args):
    print("\n$ " + " ".join(str(x) for x in args), flush=True)
    subprocess.run([str(x) for x in args], check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    p.add_argument("--steps", nargs="+", choices=STEPS, default=list(STEPS))
    a = p.parse_args()
    c = load_config(a.config)
    project = c["project_dir"]
    py = sys.executable

    if "rasters" in a.steps:
        run(py, os.path.join(HERE, "glacier_rasters.py"), a.config)
    if "extend" in a.steps:
        run(py, os.path.join(HERE, "glacier_extend.py"), a.config)
    if "hrus" in a.steps:
        run(py, os.path.join(HERE, "hru_attributes.py"), a.config)
    if "zonal" in a.steps:
        run(py, os.path.join(HERE, "glacier_zonal_stats.py"), a.config)
    if "forcing" in a.steps:
        forcing = os.path.join(project, "forcing", "SUMMA_input")
        attributes = os.path.join(project, "settings", "SUMMA", "attributes.nc")
        args = [py, os.path.join(HERE, "correct_forcing_to_station.py"), forcing,
                os.path.join(project, c["stations"]), attributes, os.path.join(forcing, "station_corrected")]
        if c.get("stakes"):
            args += ["--stakes", os.path.join(project, c["stakes"])]
        if c.get("gauge_shield"):
            args += ["--gauge-shield", c["gauge_shield"]]
        campaign = c.get("spechum_campaign")
        if campaign:
            ratios = os.path.join(project, campaign["ratios"])
            run(py, os.path.join(HERE, "spechum_ratio_from_campaign.py"), forcing, attributes,
                os.path.join(project, campaign["station"]), campaign["latitude"], campaign["longitude"], ratios)
            args += ["--spechum-ratios", ratios]
        run(*args)
    if "coldstate" in a.steps:
        run(py, os.path.join(HERE, "glacier_cold_state.py"), project, "--utm-epsg", c["utm_epsg"],
            "--start", c.get("cold_start", "2008-01"), "--soil-offset", c.get("soil_offset", 1.5),
            "--ice-temp", c.get("ice_temp", -5.0))


if __name__ == "__main__":
    main()
