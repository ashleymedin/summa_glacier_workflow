#!/bin/zsh
# Figure 7 (lake_heat) on round-3 trial 405: the lake held full, filling with all its sediment trapped, and settling with
# the fetch roughness; no lake and settling (the case as built) are run_r3's sample_405_nolake and sample_405_settle.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
export OMPI_MCA_mpi_yield_when_idle=1
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow)
L=../scratch/2026-11-19
$PY rerun_trials.py wolverine_stream calibration_r3 405 $X --set wetlandSedConc=0 --label lake > $L/w_lake_full.log 2>&1 &
$PY rerun_trials.py wolverine_stream calibration_r3 405 $X --set wetlandSedConc=0.0000562 --set wetlandSettleVel=1.0 --label infill > $L/w_infill.log 2>&1 &
$PY rerun_trials.py wolverine_stream calibration_r3 405 $X --set lakeFetch=200 --label fetch > $L/w_fetch.log 2>&1 &
wait
echo all done
