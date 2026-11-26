#!/bin/bash
# SUMMA drop-wetland-air against its parent (summa_r10, same physics otherwise): round 9's 465 on the delta case at default lake air and wind, both builds.
cd "$(dirname "$0")/../../../runs"; export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH OMPI_MCA_mpi_yield_when_idle=1
O=../scratch/2026-11-26/stream_cheap_r9; X="--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow"
for b in r10 dropair; do
  SUMMA_DIR=$HOME/Research/SummaSundials/summa_$b python rerun_trials.py wolverine_stream_delta calibration_r9 465 $X --set wetlandPoolCooling=3 --label drop_$b < /dev/null > $O/drop_$b.log 2>&1 || echo "drop_$b failed" >> $O/drop_$b.log &
done; wait
