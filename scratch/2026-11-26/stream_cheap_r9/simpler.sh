#!/bin/bash
# stream_cheap_r9's trial 79 as found (old code), then on the drop-wetland-air build with the lake's wind and air cooling gone (wind 1, cooling 0)
cd "$(dirname "$0")/../../../runs"; export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH OMPI_MCA_mpi_yield_when_idle=1
O=../scratch/2026-11-26/stream_cheap_r9; X="--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow"
[ -d wolverine_stream_delta/stream_cheap_r9_rerun/sample_79_as_found/output ] || \
  SUMMA_DIR=$HOME/Research/SummaSundials/summa_next python rerun_trials.py wolverine_stream_delta stream_cheap_r9 79 $X --label as_found < /dev/null > $O/as_found.log 2>&1 || echo "as_found failed" >> $O/as_found.log
SUMMA_DIR=$HOME/Research/SummaSundials/summa_dropair python rerun_trials.py wolverine_stream_delta stream_cheap_r9 79 $X --drop wetlandWindFactor --drop wetlandAirCooling --label no_wind_air < /dev/null > $O/no_wind_air.log 2>&1 || echo "no_wind_air failed" >> $O/no_wind_air.log
