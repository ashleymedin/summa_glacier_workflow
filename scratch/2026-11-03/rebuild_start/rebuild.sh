#!/bin/bash
# Rebuild both setups of both basins on the Copernicus glacier surface (glacier_dem), then their cases and spin-ups.
set -e
cd "$(dirname "$0")/../../.."
PY=~/miniconda3/envs/glacier/bin/python
for b in wolverine gulkana; do
  $PY setup_glacier_domain.py domains/${b}_general.yaml --steps rasters extend bands hrus zonal era5 coldstate
  $PY setup_glacier_domain.py domains/${b}.yaml --steps rasters extend bands hrus zonal
  $PY remap_forcing.py domains/${b}.yaml
  $PY setup_glacier_domain.py domains/${b}.yaml --steps forcing coldstate
  $PY run_study.py $b --steps cases spinup
done
