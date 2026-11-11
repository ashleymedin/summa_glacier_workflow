#!/bin/bash
# 11 Nov: the two general cases again with precipElevGrad searched from the ERA5 cells' height (forcingElev, summa 889b2fca)
# and frozenPrecipMultip over 0.3-2.0; 32 x 15, then post_cal.py.
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
for c in wolverine_general gulkana_general; do
  $PY calibrate.py calibrate $c --search domain --population 32 --generations 15 --ranks 4 --name calibration \
    > logs/2026-11-11/calibrate_$c.log 2>&1 &
  $PY ../scratch/2026-11-11/overnight/post_cal.py $c > logs/2026-11-11/post_driver_$c.log 2>&1 &
done
wait
