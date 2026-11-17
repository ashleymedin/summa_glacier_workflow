#!/bin/bash
# stability and measurement-height sensitivity, after batch1
cd "$(dirname "$0")"
PY=~/miniconda3/envs/glacier/bin/python
until grep -q "batch1 done" batch1.log; do sleep 30; done
run() { $PY exp.py run "$@"; }
for c in gulkana_added wolverine_added; do
  run $c mahrt --decision astability=mahrtexp &
  run $c mh20 --attr mHeight@1=2.0; wait
done
echo batch2 done
