#!/bin/bash
# Round 5's general pair on Millan's bed with no strip melt-out: both general domains rebuilt and spun up, then calibrated
# once the added pair is done.
cd "$(dirname "$0")/../../.."
PY=~/miniconda3/envs/glacier/bin/python
L=runs/logs/2026-11-19r5
for b in gulkana wolverine; do
  $PY setup_glacier_domain.py domains/${b}_general.yaml --steps rasters extend bands hrus vegetation zonal era5 coldstate > $L/setup_${b}_general_millan.log 2>&1 || { echo "setup $b failed"; exit 1; }
done
$PY build_cases.py cases.yaml wolverine_general gulkana_general > $L/build_general_millan.log 2>&1 || { echo "build failed"; exit 1; }
cd runs
for c in wolverine_general gulkana_general; do $PY spinup.py $c > logs/2026-11-19r5/spinup_${c}_millan.log 2>&1 & done
wait
echo "rebuild done"
until grep -q "done wolverine_added gulkana_added" logs/2026-11-19r5/run_added.log 2>/dev/null; do sleep 120; done
bash ../scratch/2026-11-19/paper1r5/run.sh "wolverine_general gulkana_general"
