#!/bin/bash
# Calibrate the added cases with the katabatic-fetch binary, glacier cooling constant (glacierTempReduction 0.733)
# against fetch along the flowline (glacierCoolLength 5281 m), both on today's frozen forcing: 32 x 15, then post_cal.py.
#     caffeinate -ims scratch/2026-11-12/fetch/calibrate_ab.sh
cd "$(dirname "$0")/../../../runs"
export SUMMA_DIR=/Users/amedin/Research/SummaSundials/summa_katabatic
PY=~/miniconda3/envs/glacier/bin/python
LOGS=logs/2026-11-12/fetch
mkdir -p $LOGS
for basin in wolverine gulkana; do
  pids=""
  for v in const fetch; do
    c=${basin}_added_$v
    $PY calibrate.py calibrate $c --search domain --population 32 --generations 15 --ranks 5 --name calibration \
      > $LOGS/calibrate_$c.log 2>&1 & pids="$pids $!"
    $PY ../scratch/2026-11-11/overnight/post_cal.py $c 2026-11-12/fetch > $LOGS/post_driver_$c.log 2>&1 &
  done
  wait $pids
  echo "$(date '+%m-%d %H:%M') calibrated $basin" >> $LOGS/ab.log
done
wait
echo "$(date '+%m-%d %H:%M') done" >> $LOGS/ab.log
