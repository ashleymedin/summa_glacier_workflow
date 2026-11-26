#!/bin/bash
# stream_cheap_r9's front (one trial, 79, and its duplicates) evaluated on the code it ran on (summa_next bf5ddb11), WY2006-26.
cd "$(dirname "$0")/../../../runs"; export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH SUMMA_DIR=$HOME/Research/SummaSundials/summa_next OMPI_MCA_mpi_yield_when_idle=1
python calibrate.py evaluate wolverine_stream_delta --name stream_cheap_r9 --ranks 2 --jobs 2 < /dev/null > ../scratch/2026-11-26/stream_cheap_r9/evaluate.log 2>&1 || echo failed >> ../scratch/2026-11-26/stream_cheap_r9/evaluate.log
