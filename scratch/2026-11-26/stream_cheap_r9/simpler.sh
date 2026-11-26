#!/bin/bash
# stream_cheap_r9's trial 79 rerun with the lake's wind and air left alone (wetlandWindFactor 1, wetlandAirCooling 0): can both be dropped from the search?
cd "$(dirname "$0")/../../../runs"; export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH SUMMA_DIR=$HOME/Research/SummaSundials/summa_next OMPI_MCA_mpi_yield_when_idle=1
O=../scratch/2026-11-26/stream_cheap_r9; X="--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow"
python rerun_trials.py wolverine_stream_delta stream_cheap_r9 79 $X --label as_found < /dev/null > $O/as_found.log 2>&1 || echo "as_found failed" >> $O/as_found.log
python rerun_trials.py wolverine_stream_delta stream_cheap_r9 79 $X --set wetlandWindFactor=1 --set wetlandAirCooling=0 --label no_wind_air < /dev/null > $O/no_wind_air.log 2>&1 || echo "no_wind_air failed" >> $O/no_wind_air.log
