#!/bin/bash
# Trial 79 of stream_cheap_r9 on the drop-wetland-air build with the reach's heat terms written, to find where May's warmth comes from
cd "$(dirname "$0")/../../../runs"; export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH OMPI_MCA_mpi_yield_when_idle=1 SUMMA_DIR=$HOME/Research/SummaSundials/summa_dropair
X=""; for v in scalarStreamTemp scalarStreamOutflow scalarStreamLatInflow scalarLakeIceThick scalarStreamLatInflowTemp scalarStreamInflowTemp \
  scalarStreamFrictionHeat averageRoutedRunoffTemp scalarAquiferTemp scalarHypTemp scalarStreamSfcInflowTemp; do X="$X --extra $v"; done
python rerun_trials.py wolverine_stream_delta stream_cheap_r9 79 $X --drop wetlandWindFactor --drop wetlandAirCooling --label diag < /dev/null > ../scratch/2026-11-26/may_warm/diag.log 2>&1 || echo "diag failed" >> ../scratch/2026-11-26/may_warm/diag.log
