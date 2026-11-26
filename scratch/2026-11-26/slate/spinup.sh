#!/bin/bash
# Slate Creek: 30 cycles of WY2005 for the three deep thermal options, on the frozen build
cd "$(dirname "$0")/../../../runs"
export SUMMA_DIR=~/Research/SummaSundials/summa_r10 OMPI_MCA_mpi_yield_when_idle=1
for c in slate_stream slate_stream_none slate_stream_airgw; do
  ~/miniconda3/envs/glacier/bin/python spinup.py $c > ../scratch/2026-11-26/slate/spinup_$c.log 2>&1 &
done
wait
