#!/bin/bash
# The rain-snow profile twin on both general cases, Wolverine first: truth, then the control at the truth and three wrong splits.
cd "$(dirname "$0")"
export OMPI_MCA_mpi_yield_when_idle=1
PY=/Users/amedin/miniconda3/envs/glacier/bin/python
for c in wolverine_general gulkana_general; do
  $PY twin_profile.py truth $c > twin_truth_$c.log 2>&1 || continue
  for p in truth default cold1K narrow; do
    $PY twin_profile.py point $c $p --population 12 --generations 8 --ranks 5 > twin_${c}_$p.log 2>&1
  done
  $PY twin_profile.py report $c > twin_report_$c.txt 2>&1
done
