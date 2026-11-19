#!/bin/bash
# 19 Nov: the four paper-1 cases, round 5b (see round5b.sh),
# two at a time (4 ranks each), each pair's post_cal.py before the next.
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-19r5b
export OMPI_MCA_mpi_yield_when_idle=1
for pair in "$@"; do
  for c in $pair; do
    ( $PY calibrate.py calibrate $c --search domain --population 32 --generations 15 --ranks 4 --name calibration \
        > $L/calibrate_$c.log 2>&1 || echo "calibration exited $?" >> $L/calibrate_$c.log
      $PY ../scratch/2026-11-17/paper1/post_cal.py $c 2026-11-19r5b > $L/post_driver_$c.log 2>&1 ) &
  done
  wait
done
echo "done $*"
