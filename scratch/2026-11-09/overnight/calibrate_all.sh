#!/bin/bash
# Overnight 9 Nov: the four cases' domain-search NSGA-II calibrations at once (24 x 8, 4 ranks each).
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
for c in wolverine_general wolverine_added gulkana_general gulkana_added; do
  $PY calibrate.py calibrate $c --search domain --population 24 --generations 8 --ranks 4 --name calibration \
    > logs/2026-11-09/calibrate_$c.log 2>&1 &
done
wait
