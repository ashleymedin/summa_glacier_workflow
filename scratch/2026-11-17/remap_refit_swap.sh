#!/bin/bash
# Remap the four glacier domains with the re-fetched 4 Dec 2019 levels, refit the station correction, and swap it in.
set -e
cd "$(dirname "$0")/../.."
PY=/Users/amedin/miniconda3/envs/glacier/bin/python
for d in wolverine gulkana wolverine_general gulkana_general; do $PY remap_forcing.py domains/$d.yaml > scratch/2026-11-17/remap_$d.log 2>&1; echo "remapped $d"; done
rm -rf data/domain_Wolverine/forcing/station_corrected_v3 data/domain_Gulkana/forcing/station_corrected_v3
$PY scratch/2026-11-16/refit_station_corrected.py
for D in Wolverine Gulkana; do
  F=data/domain_$D/forcing
  mv $F/SUMMA_input/station_corrected $F/station_corrected_interp201912
  mv $F/station_corrected_v3 $F/SUMMA_input/station_corrected
  echo "swapped $D"
done
