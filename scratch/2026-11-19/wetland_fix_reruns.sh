#!/bin/zsh
# Every round-3 stream rerun with a wetland, redone on the SUMMA build whose shallow wetlands freeze solid in their water
# layers (the delta's 14 March 2015 failure); the no-lake and no-fan runs have no wetland and are kept.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
export OMPI_MCA_mpi_yield_when_idle=1
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow)
L=../scratch/2026-11-19
$PY rerun_trials.py wolverine_stream calibration_r3 405 $X --label settle > $L/w_settle.log 2>&1 &
$PY rerun_trials.py wolverine_stream calibration_r3 405 $X --set wetlandSedConc=0 --label lake > $L/w_lake_full.log 2>&1 &
$PY rerun_trials.py wolverine_stream calibration_r3 405 $X --set wetlandSedConc=0.0000562 --set wetlandSettleVel=1.0 --label infill > $L/w_infill.log 2>&1 &
$PY rerun_trials.py wolverine_stream calibration_r3 405 $X --set lakeFetch=200 --label fetch > $L/w_fetch.log 2>&1 &
wait
$PY rerun_trials.py wolverine_stream_delta calibration_r3 405 $X --label delta > $L/w_delta.log 2>&1 &
$PY rerun_trials.py gulkana_stream calibration_r3 467 $X --label fan > $L/g_fan.log 2>&1 &
$PY rerun_trials.py gulkana_stream calibration_r3 467 $X --set wetlandMaxArea=40000 --set wetlandFlatArea=53000 --label scale > $L/g_scale.log 2>&1 &
wait
echo all done
