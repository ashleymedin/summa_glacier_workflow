#!/bin/bash
# Round 9 balanced trials rerun with capillary retention changed only: 4% everywhere, 1% at Wolverine.
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-25check
mkdir -p $L
export OMPI_MCA_mpi_yield_when_idle=1
run() { $PY rerun_trials.py $1 $2 $3 --set Fcapil=$4 --label fcapil$5 --ranks 2 > $L/fcapil_$1_$5.log 2>&1; }
run wolverine_general calibration_s43 479 0.04 04 &
run gulkana_general calibration_s43 474 0.04 04 &
run wolverine_added calibration 465 0.04 04 &
run gulkana_added calibration_s43 413 0.04 04 &
wait
run wolverine_general calibration_s43 479 0.01 01 &
run wolverine_added calibration 465 0.01 01 &
wait
echo "retention reruns done"
