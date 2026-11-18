#!/bin/bash
# 18 Nov: the four paper-1 cases, round 3: Site B melting-snow albedo floor, basin-wide general wind, rain gradient above the gauges,
# two at a time (4 ranks each), each pair's post_cal.py before the next.
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-18r3
export OMPI_MCA_mpi_yield_when_idle=1
for pair in "wolverine_added gulkana_added" "wolverine_general gulkana_general"; do
  for c in $pair; do
    ( $PY calibrate.py calibrate $c --search domain --population 32 --generations 15 --ranks 4 --name calibration \
        > $L/calibrate_$c.log 2>&1 || echo "calibration exited $?" >> $L/calibrate_$c.log
      $PY ../scratch/2026-11-17/paper1/post_cal.py $c 2026-11-18r3 > $L/post_driver_$c.log 2>&1 ) &
  done
  wait
done
echo all done
