#!/bin/bash
# 11 Nov, second run: the two general cases on raw ERA5 scaled per HRU by the CHELSA ratio (37839dd), precipElevGrad
# not searched, frozenPrecipMultip over 0.3-2.0; 32 x 15, then post_cal.py. Logs in runs/logs/2026-11-11/chelsa.
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
mkdir -p logs/2026-11-11/chelsa
for c in wolverine_general gulkana_general; do
  $PY calibrate.py calibrate $c --search domain --population 32 --generations 15 --ranks 4 --name calibration \
    > logs/2026-11-11/chelsa/calibrate_$c.log 2>&1 &
  $PY ../scratch/2026-11-11/overnight/post_cal.py $c 2026-11-11/chelsa > logs/2026-11-11/chelsa/post_driver_$c.log 2>&1 &
done
wait
