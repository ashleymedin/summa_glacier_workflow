#!/bin/bash
# Both general domains rebuilt on the slowed melt-out bed, their cases rebuilt and spun up.
cd "$(dirname "$0")/../../.."
PY=~/miniconda3/envs/glacier/bin/python
L=runs/logs/2026-11-19r5
for b in gulkana wolverine; do
  $PY setup_glacier_domain.py domains/${b}_general.yaml --steps rasters extend bands hrus vegetation zonal era5 coldstate > $L/setup_${b}_general.log 2>&1 || { echo "setup $b failed"; exit 1; }
done
$PY build_cases.py cases.yaml wolverine_general gulkana_general > $L/build_general.log 2>&1 || { echo "build failed"; exit 1; }
cd runs
for c in wolverine_general gulkana_general; do $PY spinup.py $c > logs/2026-11-19r5/spinup_$c.log 2>&1 & done
wait
echo rebuild done
