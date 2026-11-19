#!/bin/bash
# Gulkana general rebuilt from its extension (terminus fallback in glacier_extend.py) before round 5b's general pair starts.
cd "$(dirname "$0")/../../.."
PY=~/miniconda3/envs/glacier/bin/python
L=runs/logs/2026-11-19r5b
$PY setup_glacier_domain.py domains/gulkana_general.yaml --steps bands hrus vegetation zonal era5 coldstate > $L/setup_gulkana_general_room.log 2>&1 || { echo "setup failed"; exit 1; }
$PY build_cases.py cases.yaml gulkana_general > $L/build_gulkana_general_room.log 2>&1 || { echo "build failed"; exit 1; }
cd runs && $PY spinup.py gulkana_general > logs/2026-11-19r5b/spinup_gulkana_general_room.log 2>&1 || { echo "spinup failed"; exit 1; }
echo "gulkana_general room rebuild done"
