#!/bin/bash
# Round 9's balanced added-data trials over the calibration years on round 10's binary (summa_r10, label jbase) and on the
# infiltration-heat Jacobian (summa_jac at 1724f4c1, label jnew); each pair runs together so their wall times share the load.
cd "$(dirname "$0")/../../../runs"; export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH OMPI_MCA_mpi_yield_when_idle=1
L=logs/2026-11-26/jacobian; mkdir -p $L
one() { s=$(date +%s); SUMMA_DIR=$HOME/Research/SummaSundials/$1 python rerun_trials.py $3 $4 $5 --aligned --calibration-years --label $2 \
  < /dev/null > $L/$3_$2.log 2>&1 || echo "$3 $2 failed"; echo "$3 $2 $(( $(date +%s) - s )) s" >> $L/times.txt; }
for s in "wolverine_added calibration_1125r9 465" "gulkana_added calibration_s43_1125r9 413"; do
  one summa_r10 jbase $s & one summa_jac jnew $s & wait
done; echo done
