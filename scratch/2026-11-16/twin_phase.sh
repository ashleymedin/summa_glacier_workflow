#!/bin/bash
# The phase twin on both general cases, Wolverine first; run under caffeinate -ims.
set -e
export SUMMA_DIR=/Users/amedin/Research/SummaSundials/summa_snowmult
PY=/Users/amedin/miniconda3/envs/glacier/bin/python
cd "$(dirname "$0")"
for case in wolverine_general gulkana_general; do
  [ -d ../../runs/$case/twin_phase/obs ] || $PY twin.py truth $case phase
  $PY twin.py calibrate $case phase --population 16 --generations 10 --ranks 8
done
