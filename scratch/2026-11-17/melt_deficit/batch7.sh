#!/bin/bash
# what's left: glacier snowfall multiplier off May-Aug (throwaway build summa_seasmult), and an albedo decay sweep on the fix
cd "$(dirname "$0")"
PY=~/miniconda3/envs/glacier/bin/python
run() { nice $PY exp.py run "$@"; }
SUMMA_DIR=/Users/amedin/Research/SummaSundials/summa_seasmult run gulkana_added seasmult &
SUMMA_DIR=/Users/amedin/Research/SummaSundials/summa_seasmult run wolverine_added seasmult; wait
export SUMMA_DIR=/Users/amedin/Research/SummaSundials/summa_mahrt
for c in gulkana_added wolverine_added; do
  run $c gm_decay05 --param albedoDecayRate=0.5d+6 &
  run $c gm_decay02 --param albedoDecayRate=0.2d+6; wait
done
echo batch7 done
