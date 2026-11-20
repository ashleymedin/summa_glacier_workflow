#!/bin/bash
# Round 6: round-5b inputs (fixed SoilGrids upland soil) with the upland and glacier snowfall multipliers searched over 0.2-5;
# round 5b kept as calibration*_1120r5b. Each argument is a set of cases run together, 4 ranks each, post_cal.py after each;
# the general pair first, the added pair only if Gulkana general reaches round 4.
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-20r6
mkdir -p $L
export OMPI_MCA_mpi_yield_when_idle=1
for pair in "$@"; do
  for c in $pair; do
    ( $PY calibrate.py calibrate $c --search domain --population 32 --generations 15 --ranks 4 --name calibration \
        > $L/calibrate_$c.log 2>&1 || echo "calibration exited $?" >> $L/calibrate_$c.log
      $PY ../scratch/2026-11-17/paper1/post_cal.py $c 2026-11-20r6 > $L/post_driver_$c.log 2>&1 ) &
  done
  wait
done
echo "round 6 done $*"
