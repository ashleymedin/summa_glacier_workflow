#!/bin/zsh
# 20 Nov, Paper 2 Stage B on Wolverine: the 5b domain search and the stream's four parameters, scored on discharge, seasonal
# balance and water temperature, once round 5b (round5b.sh) has finished; 5b's balanced trial left May at 0.5-0.7 of the gauge,
# which neither discharge KGE nor the balance constrains.
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
OUT=../scratch/2026-11-20/stage_b
export OMPI_MCA_mpi_yield_when_idle=1
while pgrep -f "paper1r5/round5b.sh" > /dev/null; do sleep 120; done
echo "$(date '+%d %H:%M') round 5b done; stage B starts"
$PY calibrate.py calibrate wolverine_stream_delta --search stream --population 32 --generations 15 --ranks 9 \
  --name stream_b > $OUT/wolverine.log 2>&1 || { echo "stage B exited $?"; exit 1; }
$PY calibrate.py evaluate wolverine_stream_delta --name stream_b --ranks 2 --jobs 4 >> $OUT/wolverine.log 2>&1
echo "$(date '+%d %H:%M') stage B Wolverine done"
