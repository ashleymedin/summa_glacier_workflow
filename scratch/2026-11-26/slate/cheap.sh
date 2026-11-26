#!/bin/bash
# Slate Creek cheap search (12 x 8, 4 ranks): discharge and water temperature, WY2006-09, then its front on WY2010-Dec 2011
cd "$(dirname "$0")/../../../runs"
export SUMMA_DIR=~/Research/SummaSundials/summa_r10 OMPI_MCA_mpi_yield_when_idle=1
PY=~/miniconda3/envs/glacier/bin/python; L=../scratch/2026-11-26/slate
$PY calibrate.py calibrate slate_stream --search domain --population 12 --generations 8 --ranks 4 --seed 42 --name cheap > $L/cheap.log 2>&1 &&
$PY calibrate.py evaluate slate_stream --name cheap --ranks 2 --jobs 2 > $L/cheap_evaluate.log 2>&1
