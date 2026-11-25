#!/bin/bash
# After the cheap search: Gulkana's fan with the four wetland lines gulkana_stream's older inputs hold (lines) and the flow-scaled fan.
cd "$(dirname "$0")/../../../runs"; export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH SUMMA_DIR=$HOME/Research/SummaSundials/summa_next OMPI_MCA_mpi_yield_when_idle=1
while pgrep -f "calibrate.py calibrate wolverine_stream_delta.*stream_cheap_r9" > /dev/null; do sleep 30; done
X="--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow --inputs gulkana_stream_fan/summa_inputs_lines"; L=logs/2026-11-25/stream_r9
python rerun_trials.py gulkana_stream calibration_r9 413 $X --label lines > $L/g_lines.log 2>&1 < /dev/null || echo "g_lines failed"
python rerun_trials.py gulkana_stream calibration_r9 413 $X --set wetlandMaxArea=40000 --set wetlandFlatArea=53000 --label scale > $L/g_scale.log 2>&1 < /dev/null || echo "g_scale failed"
echo "post done"
