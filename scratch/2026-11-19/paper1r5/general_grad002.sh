#!/bin/bash
# Round 5's general pair with the glacier snowfall gradient 0.002 m-1 (median of six USGS glaciers' winter-balance slopes):
# both general cases rebuilt from their domains (unchanged), spun up and calibrated.
cd "$(dirname "$0")/../../.."
PY=~/miniconda3/envs/glacier/bin/python
L=runs/logs/2026-11-19r5
$PY build_cases.py cases.yaml wolverine_general gulkana_general > $L/build_general_grad002.log 2>&1 || { echo "build failed"; exit 1; }
cd runs
for c in wolverine_general gulkana_general; do $PY spinup.py $c > logs/2026-11-19r5/spinup_${c}_grad002.log 2>&1 & done
wait
echo "rebuild done"
bash ../scratch/2026-11-19/paper1r5/run.sh "wolverine_general gulkana_general"
