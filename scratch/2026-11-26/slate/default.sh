#!/bin/bash
# Slate Creek default-parameter routed runs of the three deep thermal options, two drivers of 2 ranks at a time, on the frozen build
cd "$(dirname "$0")/../../.."
export SUMMA_DIR=~/Research/SummaSundials/summa_r10 OMPI_MCA_mpi_yield_when_idle=1
PY=~/miniconda3/envs/glacier/bin/python; D=scratch/2026-11-26/slate
$PY $D/slate_default.py slate_stream slate_stream_airgw > $D/default_a.log 2>&1 &
$PY $D/slate_default.py slate_stream_none > $D/default_b.log 2>&1 &
wait
$PY $D/slate_default.py --score slate_stream slate_stream_none slate_stream_airgw > $D/default_scores.log 2>&1
