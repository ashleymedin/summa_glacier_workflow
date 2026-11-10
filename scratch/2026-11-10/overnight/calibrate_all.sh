#!/bin/bash
# Overnight 10-11 Nov: the four paper cases with Andreas, windExposure 0.5943 (added), spun up; 32 x 15, then post_cal.py.
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
for c in wolverine_general wolverine_added gulkana_general gulkana_added; do
  $PY calibrate.py calibrate $c --search domain --population 32 --generations 15 --ranks 4 --name calibration \
    > logs/2026-11-10/calibrate_$c.log 2>&1 &
  $PY ../scratch/2026-11-10/overnight/post_cal.py $c > logs/2026-11-10/post_driver_$c.log 2>&1 &
done
wait
