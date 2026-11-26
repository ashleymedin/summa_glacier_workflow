#!/bin/bash
# slate_stream_lat cheap search (12 x 8, 4 ranks, seed 42, as cheap.sh) once lat.sh's default run is done, then its held-out evaluation
cd "$(dirname "$0")/../../../runs"
export SUMMA_DIR=~/Research/SummaSundials/summa_r10 OMPI_MCA_mpi_yield_when_idle=1
PY=~/miniconda3/envs/glacier/bin/python; L=../scratch/2026-11-26/slate
while pgrep -f '\./lat\.sh$' > /dev/null; do sleep 60; done
$PY calibrate.py calibrate slate_stream_lat --search domain --population 12 --generations 8 --ranks 4 --seed 42 --name cheap > $L/cheap_lat.log 2>&1 &&
$PY calibrate.py evaluate slate_stream_lat --name cheap --ranks 2 --jobs 2 > $L/cheap_lat_evaluate.log 2>&1
