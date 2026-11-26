#!/bin/bash
# slate_stream_lat (bbLatflow): 30 cycles of WY2005, then the default-parameter run scored at the gauge
cd "$(dirname "$0")/../../../runs"
export SUMMA_DIR=~/Research/SummaSundials/summa_r10 OMPI_MCA_mpi_yield_when_idle=1
PY=~/miniconda3/envs/glacier/bin/python; L=../scratch/2026-11-26/slate
$PY spinup.py slate_stream_lat > $L/spinup_slate_stream_lat.log 2>&1 &&
$PY $L/slate_default.py slate_stream_lat > $L/default_lat.log 2>&1
