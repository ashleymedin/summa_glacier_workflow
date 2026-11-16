#!/bin/bash
# Calibrate the general pair on the pressure-level forcing (the tail of deploy_levels.sh for the general cases).
cd "$(dirname "$0")/../.." || exit 1
PY=/Users/amedin/miniconda3/envs/glacier/bin/python
LOGS=runs/logs/2026-11-16
for c in wolverine_general gulkana_general; do
  for f in calibration calibration_rerun calibration_evaluation; do
    [ -d runs/$c/$f ] && [ ! -e runs/$c/${f}_chelsa ] && mv runs/$c/$f runs/$c/${f}_chelsa
  done
done
cd runs
pids=""
for c in wolverine_general gulkana_general; do
  $PY calibrate.py calibrate $c --search domain --population 32 --generations 15 --ranks 4 --name calibration \
    > logs/2026-11-16/calibrate_$c.log 2>&1 & pids="$pids $!"
  $PY ../scratch/2026-11-11/overnight/post_cal.py $c 2026-11-16 > logs/2026-11-16/post_driver_$c.log 2>&1 &
done
wait $pids
wait
echo "$(date '+%m-%d %H:%M') calibrated: general" >> logs/2026-11-16/general.log
