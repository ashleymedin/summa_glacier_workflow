#!/bin/bash
# Warm valley air at Wolverine (glacier cooling none on HRU 1, Site B's on HRU 2, more on HRU 3), Gulkana added's upland
# snowfall x1.5, and Wolverine added with the snow albedo written, for the firn exposure of warm summers.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-19
S=../scratch/2026-11-19
export OMPI_MCA_mpi_yield_when_idle=1
X="--targets discharge,mass_balance,wgms_amce --aligned --ranks 2"
for v in scalarSenHeatGround scalarLatHeatGround scalarGroundAbsorbedSolar scalarLWNetGround scalarGroundNetNrgFlux scalarSnowAlbedo; do X="$X --extra $v"; done
$PY rerun_trials.py wolverine_added calibration 405 $X --inputs $S/inputs_wolverine_added_valley --label valley > $L/wolverine_added_valley.log 2>&1 &
$PY rerun_trials.py wolverine_general calibration 452 $X --inputs $S/inputs_wolverine_general_valley --label valley > $L/wolverine_general_valley.log 2>&1 &
$PY rerun_trials.py gulkana_added calibration 467 $X --inputs $S/inputs_gulkana_added_upland15 --label upland15 > $L/gulkana_added_upland15.log 2>&1 &
$PY rerun_trials.py wolverine_added calibration 405 $X --label alb > $L/wolverine_added_alb.log 2>&1 &
wait
echo screen7 done
