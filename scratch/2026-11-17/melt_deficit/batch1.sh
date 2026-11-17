#!/bin/bash
# one-change sensitivity of the summer stake balances, two runs at a time
cd "$(dirname "$0")"
PY=~/miniconda3/envs/glacier/bin/python
run() { $PY exp.py run "$@"; }
for c in gulkana_added wolverine_added; do
  run $c refresh10 --param albedoRefresh=10 &
  run $c decay03 --param albedoDecayRate=0.3d+6; wait
  run $c minspr45 --param albedoMinSpring=0.45 &
  run $c mh15 --attr mHeight=1.5; wait
  run $c wind1 --param glacierWindFactor=1.0 &
  run $c cool1 --param glacierTempReduction=1.0; wait
done
echo batch1 done
