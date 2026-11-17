#!/bin/bash
# the glacier-meas-height binary: alone, and with Mahrt stability
cd "$(dirname "$0")"
PY=~/miniconda3/envs/glacier/bin/python
export SUMMA_DIR=/Users/amedin/Research/SummaSundials/summa_measheight
until grep -q "batch3 done" batch3.log; do sleep 20; done
run() { $PY exp.py run "$@"; }
for c in gulkana_added wolverine_added; do
  run $c gmh &
  run $c gmh_mahrt --decision astability=mahrtexp; wait
done
echo batch4 done
