#!/usr/bin/env python3
"""Run the glacier setup of a domain in data/, step by step, from its domain YAML.

Steps, in order (--steps picks some; the default is all of them):

  seed      seed_domain.py: a domain with seed_from (the general setup) starts from its source's static files
  nhd       acquire_nhd.py: the USGS watershed (HUC12), flowlines and lakes around the domain, for basin_within and the plots
  rasters   glacier_rasters.py: domain type, RGI id, debris thickness and bed rasters
  extend    glacier_extend.py: basin on the bed, glacier-capable cells downstream (needs pysheds)
            -- then, in SYMFLUENCE: elevation-band HRUs, upland attributes.nc and coldState.nc --
  bands     make_hrus.py: the HRUs, elevation bands of the surface cut to the basin and the glaciers in it
  hrus      hru_attributes.py: HRU area, centre, elevation, slope and contour length from the polygons and DEM
  zonal     glacier_zonal_stats.py: per-HRU debris, domain-type, elevation, slope and aspect statistics
  era5      acquire_era5.py over the YAML's forcing_period (months not yet in forcing/raw_data), then
            remap_forcing.py: forcing/SUMMA_input
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
STEPS = ("seed", "nhd", "rasters", "extend", "bands", "hrus", "zonal", "era5", "forcing", "coldstate")
SEEDED = ("seed", "rasters", "extend", "bands", "hrus", "zonal", "era5", "coldstate")  # raw ERA5 is read from the source domain; no station correction


def run(*args):
    print("\n$ " + " ".join(str(x) for x in args), flush=True)
    subprocess.run([str(x) for x in args], check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("config", help="domain YAML in domains/")
    p.add_argument("--steps", nargs="+", choices=STEPS)
    a = p.parse_args()
    c = load_config(a.config)
    a.steps = a.steps or list(SEEDED if c.get("seed_from") else [s for s in STEPS if s != "seed"])
    project = c["project_dir"]
    py = sys.executable

    if "seed" in a.steps:
        run(py, os.path.join(HERE, "seed_domain.py"), a.config)
    if "nhd" in a.steps and c.get("basin_within") and not c.get("seed_from"):
        run(py, os.path.join(HERE, "acquire_nhd.py"), a.config)
    if "rasters" in a.steps:
        run(py, os.path.join(HERE, "glacier_rasters.py"), a.config)
    if "extend" in a.steps:
        run(py, os.path.join(HERE, "glacier_extend.py"), a.config)
    if "bands" in a.steps:
        run(py, os.path.join(HERE, "make_hrus.py"), a.config)
    if "hrus" in a.steps:
        run(py, os.path.join(HERE, "hru_attributes.py"), a.config)
    if "zonal" in a.steps:
        run(py, os.path.join(HERE, "glacier_zonal_stats.py"), a.config)
    if "era5" in a.steps:
        if not c.get("seed_from"):  # a seeded domain reads the source domain's raw_data
            run(py, os.path.join(HERE, "acquire_era5.py"), c["forcing_period"]["first"], c["forcing_period"]["last"], a.config)
        run(py, os.path.join(HERE, "remap_forcing.py"), a.config)
    if "forcing" in a.steps:
        forcing = os.path.join(project, "forcing", "SUMMA_input")
        attributes = os.path.join(project, "settings", "SUMMA", "attributes.nc")
        args = [py, os.path.join(HERE, "correct_forcing_to_station.py"), forcing,
                os.path.join(project, c["stations"]), attributes, os.path.join(forcing, "station_corrected")]
        if c.get("stakes"):
            args += ["--stakes", os.path.join(project, c["stakes"])]
        if c.get("gauge_shield"):
            args += ["--gauge-shield", c["gauge_shield"]]
        if c.get("gauge_rain"):
            args += ["--gauge-rain"]
        if c.get("fit_years"):
            args += ["--fit-years", *c["fit_years"]]
        if c.get("precip_grad"):
            args += ["--precip-grad"]
            state = os.path.join(project, "settings", "SUMMA", "coldstate_glac.nc")  # the coldstate step's, from a previous setup
            if os.path.exists(state):
                args += ["--glacier-state", state]
        campaign = c.get("spechum_campaign")
        if campaign:
            ratios = os.path.join(project, campaign["ratios"])
            run(py, os.path.join(HERE, "spechum_ratio_from_campaign.py"), forcing, attributes,
                os.path.join(project, campaign["station"]), campaign["latitude"], campaign["longitude"],
                campaign["elevation"], ratios)
            args += ["--spechum-ratios", ratios]
        run(*args)
    if "coldstate" in a.steps:
        run(py, os.path.join(HERE, "glacier_cold_state.py"), project, "--domain", c["domain"], "--utm-epsg", c["utm_epsg"],
            "--start", c.get("cold_start", "2008-01"), "--soil-offset", c.get("soil_offset", 1.5),
            "--ice-temp", c.get("ice_temp", -5.0))


if __name__ == "__main__":
    main()
