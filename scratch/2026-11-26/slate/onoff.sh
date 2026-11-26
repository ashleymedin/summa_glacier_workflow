#!/bin/bash
# Cheap trial 87 (the front's middle) rerun under each deep thermal option, each on its own spun-up inputs, 4 ranks at most
cd "$(dirname "$0")/../../../runs"
export SUMMA_DIR=~/Research/SummaSundials/summa_r10 OMPI_MCA_mpi_yield_when_idle=1
PY=~/miniconda3/envs/glacier/bin/python; L=../scratch/2026-11-26/slate
X="--extra scalarTotalET --ranks 2"
$PY rerun_trials.py slate_stream cheap 87 $X --label bedrock > $L/onoff_bedrock.log 2>&1 &
$PY rerun_trials.py slate_stream cheap 87 $X --label none --inputs slate_stream_none/summa_inputs > $L/onoff_none.log 2>&1
wait
$PY rerun_trials.py slate_stream cheap 87 $X --label airgw --inputs slate_stream_airgw/summa_inputs > $L/onoff_airgw.log 2>&1
