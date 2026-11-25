#!/bin/bash
# Round 9's balanced added-data trials on summa bca31a5b (label ahbase) and on its advective-heat branch (label ahnew); usage: r9.sh <base summa dir> <new summa dir>
cd "$(dirname "$0")/../../../runs"; export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH OMPI_MCA_mpi_yield_when_idle=1
L=logs/2026-11-25/advective_heat; mkdir -p $L
one() { SUMMA_DIR=$1 python rerun_trials.py $3 $4 $5 --aligned --label $2 $6 < /dev/null > $L/$3_$2.log 2>&1 || echo "$3 $2 failed"; }
for s in "wolverine_added calibration 465" "gulkana_added calibration_s43 413"; do
  for c in base new; do d=$1; [ $c = new ] && d=$2
    one $d ah$c $s &
    one $d ah${c}cal $s --calibration-years &
  done; wait
done; echo done
