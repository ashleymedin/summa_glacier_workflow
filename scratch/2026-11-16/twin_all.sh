#!/bin/bash
# Both twin experiments on both general cases, Wolverine first; run under caffeinate -ims.
set -e
export SUMMA_DIR=/Users/amedin/Research/SummaSundials/summa_snowmult
PY=/Users/amedin/miniconda3/envs/glacier/bin/python
cd "$(dirname "$0")"
for case in wolverine_general gulkana_general; do
  for exp in snow melt; do
    [ -d ../../runs/$case/twin_$exp/obs ] || $PY twin.py truth $case $exp
    $PY twin.py calibrate $case $exp --population 16 --generations 10 --ranks 9
  done
done
