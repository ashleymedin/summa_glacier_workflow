#!/bin/bash
# general (ERA5) setups at default parameters: current multi-calib binary and glacier-only Mahrt + 2 m
cd "$(dirname "$0")"
PY=~/miniconda3/envs/glacier/bin/python
until grep -q "batch5 done" batch5.log; do sleep 20; done
$PY exp.py run gulkana_general base & $PY exp.py run wolverine_general base; wait
export SUMMA_DIR=/Users/amedin/Research/SummaSundials/summa_mahrt
$PY exp.py run gulkana_general gmahrt & $PY exp.py run wolverine_general gmahrt; wait
echo batch6 done
