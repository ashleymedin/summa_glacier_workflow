#!/bin/bash
# 17 Nov: the four paper-1 cases on the rebuilt Wolverine forcing, two at a time (4 ranks each), each pair's
# post_cal.py (three-member rerun, evaluation at 2 ranks x 2 jobs, aligned reruns of the balanced trial) before the next.
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-17
export OMPI_MCA_mpi_yield_when_idle=1
for pair in "wolverine_added gulkana_added" "wolverine_general gulkana_general"; do
  for c in $pair; do
    ( $PY calibrate.py calibrate $c --search domain --population 32 --generations 15 --ranks 4 --name calibration \
        > $L/calibrate_$c.log 2>&1 || echo "calibration exited $?" >> $L/calibrate_$c.log
      $PY ../scratch/2026-11-17/paper1/post_cal.py $c > $L/post_driver_$c.log 2>&1 ) &
  done
  wait
done
echo all done
