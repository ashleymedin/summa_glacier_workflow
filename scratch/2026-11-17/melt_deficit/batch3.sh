#!/bin/bash
# combined: Mahrt stability + 2 m glacier measurement height on HRU 1, then with faster albedo decay
cd "$(dirname "$0")"
PY=~/miniconda3/envs/glacier/bin/python
run() { $PY exp.py run "$@"; }
for c in gulkana_added wolverine_added; do
  run $c phys --decision astability=mahrtexp --attr mHeight@1=2.0 &
  run $c phys_decay03 --decision astability=mahrtexp --attr mHeight@1=2.0 --param albedoDecayRate=0.3d+6; wait
done
echo batch3 done
