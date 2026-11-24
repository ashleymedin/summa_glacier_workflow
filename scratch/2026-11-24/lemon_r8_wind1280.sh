#!/bin/bash
# Lemon Creek added-data on the 1280 m station wind (8895944), calibrated as round 8 once round 8 (scratch/2026-11-23/r8/run.sh) exits:
# build, spinup, then seeds 42 and 43 side by side, 4 ranks each; lemon_post.py merges the fronts.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-24lemon_wind1280
mkdir -p $L
while pgrep -f "scratch/2026-11-23/r8/run.sh" > /dev/null; do sleep 300; done
echo "round 8 done $(date)" > $L/start.log
for n in calibration calibration_s43; do
  [ -d lemon_added/$n ] && mv lemon_added/$n lemon_added/${n}_airportwind
done
export OMPI_MCA_mpi_yield_when_idle=1
(cd .. && $PY build_cases.py cases.yaml lemon_added) > $L/build.log 2>&1 && $PY spinup.py lemon_added > $L/spinup.log 2>&1 || exit 1
$PY ../scratch/2026-11-24/lemon_post.py lemon_added 2026-11-24lemon_wind1280 calibration calibration_s43 > $L/post_driver.log 2>&1 &
for s in 42 43; do
  case $s in 42) n=calibration;; *) n=calibration_s$s;; esac
  $PY calibrate.py calibrate lemon_added --search domain --population 32 --generations 15 --ranks 4 --seed $s --name $n \
    < /dev/null > $L/calibrate_lemon_added_$n.log 2>&1 || echo "calibration exited $?" >> $L/calibrate_lemon_added_$n.log &
  sleep 60
done
wait
echo "lemon done $(date)" >> $L/start.log
