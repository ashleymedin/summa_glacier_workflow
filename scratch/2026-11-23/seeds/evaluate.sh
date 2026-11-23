#!/bin/bash
# Held-out scores of every front member of the seed 43 and 44 calibrations of Gulkana added-data.
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-23seeds
export OMPI_MCA_mpi_yield_when_idle=1
for s in 43 44; do
  $PY calibrate.py evaluate gulkana_added --name calibration_seed$s --ranks 2 --jobs 2 > $L/evaluate_seed$s.log 2>&1 &
done
wait
echo "evaluations done"
