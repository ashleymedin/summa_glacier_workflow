#!/bin/bash
# glacier-only Mahrt (summa_mahrt: 2 m glacier height + Mahrt on glacier and lake snow and ice), case decisions unchanged
cd "$(dirname "$0")"
PY=~/miniconda3/envs/glacier/bin/python
export SUMMA_DIR=/Users/amedin/Research/SummaSundials/summa_mahrt
until grep -q "batch4 done" batch4.log; do sleep 20; done
$PY exp.py run gulkana_added gmahrt & $PY exp.py run wolverine_added gmahrt; wait
echo batch5 done
