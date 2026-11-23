#!/bin/bash
# Gulkana added-data on round 6's setup with seeds 43 and 44 (round 6 itself is seed 42), same budget (32 x 15), to measure how
# much the balanced trial and the front depend on the search's random numbers alone.
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-23seeds
mkdir -p $L
export OMPI_MCA_mpi_yield_when_idle=1
for s in 43 44; do
  $PY calibrate.py calibrate gulkana_added --search domain --population 32 --generations 15 --ranks 4 --seed $s \
    --name calibration_seed$s > $L/calibrate_gulkana_added_seed$s.log 2>&1 &
done
wait
echo "seeds done"
