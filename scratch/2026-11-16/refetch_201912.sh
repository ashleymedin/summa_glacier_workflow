#!/bin/bash
# Re-fetch the December 2019 pressure levels of Wolverine and Gulkana from NCAR until both are written.
cd "$(dirname "$0")/../.."
PY=/Users/amedin/miniconda3/envs/glacier/bin/python
until [ -f data/domain_Wolverine/forcing/raw_levels/domain_Wolverine_ERA5_levels_201912.nc ] && [ -f data/domain_Gulkana/forcing/raw_levels/domain_Gulkana_ERA5_levels_201912.nc ]; do
  $PY acquire_era5_levels.py 2019-12 2019-12 domains/wolverine.yaml domains/gulkana.yaml --workers 2 || sleep 600
done
