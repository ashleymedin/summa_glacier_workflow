#!/bin/bash
# 17 Nov: wolverine_added again on the re-corrected Wolverine forcing: spin-up now, then calibration and post_cal.py
# once run.sh (the general pair) is done.
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-17
export OMPI_MCA_mpi_yield_when_idle=1
$PY spinup.py wolverine_added > $L/spinup_wolverine_added.log 2>&1 || { echo "spinup exited $?" >> $L/spinup_wolverine_added.log; exit 1; }
until grep -q "all done" $L/run.log; do sleep 120; done
$PY calibrate.py calibrate wolverine_added --search domain --population 32 --generations 15 --ranks 4 --name calibration \
  > $L/calibrate_wolverine_added.log 2>&1 || echo "calibration exited $?" >> $L/calibrate_wolverine_added.log
$PY ../scratch/2026-11-17/paper1/post_cal.py wolverine_added > $L/post_driver_wolverine_added.log 2>&1
echo redo done
