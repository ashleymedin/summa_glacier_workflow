#!/bin/bash
# The two added-data domains' forcing again: ERA5 cells to HRUs (remap_forcing.py), then the station correction.
cd "$(dirname "$0")/../.."
PY=~/miniconda3/envs/glacier/bin/python
mkdir -p runs/logs/2026-11-11/deploy
for d in wolverine gulkana; do
  { $PY remap_forcing.py domains/$d.yaml && $PY setup_glacier_domain.py domains/$d.yaml --steps forcing; } \
    > runs/logs/2026-11-11/deploy/forcing_$d.log 2>&1 &
done
wait
