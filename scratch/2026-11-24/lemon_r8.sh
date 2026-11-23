#!/bin/bash
# Lemon Creek added-data, calibrated as round 8 (scratch/2026-11-23/r8/run.sh): domain search, 32 x 15, seeds 42 and 43, 4 ranks.
# One seed at a time beside round 8; lemon_post.py then merges the two fronts and post-processes the picks.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-24lemon
mkdir -p $L
export OMPI_MCA_mpi_yield_when_idle=1
(cd .. && $PY build_cases.py cases.yaml lemon_added) > $L/build.log 2>&1 && $PY spinup.py lemon_added > $L/spinup.log 2>&1 || exit 1
$PY ../scratch/2026-11-24/lemon_post.py lemon_added 2026-11-24lemon calibration calibration_s43 > $L/post_driver.log 2>&1 &
for s in 42 43; do
  case $s in 42) n=calibration;; *) n=calibration_s$s;; esac
  $PY calibrate.py calibrate lemon_added --search domain --population 32 --generations 15 --ranks 4 --seed $s --name $n \
    < /dev/null > $L/calibrate_lemon_added_$n.log 2>&1 || echo "calibration exited $?" >> $L/calibrate_lemon_added_$n.log
done
wait
echo "lemon done"
