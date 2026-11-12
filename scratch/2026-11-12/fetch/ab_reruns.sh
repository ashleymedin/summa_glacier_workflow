#!/bin/bash
# Forward A/B of the glacier air cooling on the added picks with the katabatic-fetch binary: constant factor
# (glacierCoolLength 0) against fetch along the flowline (glacierCoolLength 5281 m, Site B's 0.733 at its 1640 m).
cd "$(dirname "$0")/../../../runs"
export SUMMA_DIR=/Users/amedin/Research/SummaSundials/summa_katabatic
PY=~/miniconda3/envs/glacier/bin/python
F=../scratch/2026-11-12/fetch
for L in 0 5281; do
  $PY rerun_trials.py wolverine_added calibration 459 --ranks 2 --inputs $F/inputs_wolverine_added_L$L --extra DOMfetch --label kat$L > $F/rerun_wolverine_L$L.log 2>&1 &
  $PY rerun_trials.py gulkana_added calibration 451 --ranks 2 --inputs $F/inputs_gulkana_added_L$L --extra DOMfetch --label kat$L > $F/rerun_gulkana_L$L.log 2>&1 &
done
wait
echo done > $F/ab_done
