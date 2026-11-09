#!/bin/bash
# Overnight 10 Nov: all four cases again with the tundra canopy (2.0/0.2 m, LAI 1.8): spin-up, 32 x 10, then post_cal.py.
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
for c in wolverine_general wolverine_added gulkana_general gulkana_added; do
  ( $PY spinup.py $c > logs/2026-11-09/spinup_${c}_canopy.log 2>&1 &&
    $PY calibrate.py calibrate $c --search domain --population 32 --generations 10 --ranks 4 --name calibration \
      > logs/2026-11-09/calibrate_$c.log 2>&1 ) &
  $PY ../scratch/2026-11-09/overnight/post_cal.py $c > logs/2026-11-09/post_driver_$c.log 2>&1 &
done
wait
