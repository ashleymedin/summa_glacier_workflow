#!/bin/bash
# Screening reruns of the balanced trials: the added-data cases on the rain-gradient forcing (rain_gradient_forcing.py), and the
# general cases scored against the seasonal stakes with the glacier energy terms written.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-18
export OMPI_MCA_mpi_yield_when_idle=1
X="--targets discharge,mass_balance,wgms_amce --aligned --ranks 2"
for v in scalarGlceMelt scalarSenHeatGround scalarLatHeatGround scalarGroundAbsorbedSolar scalarLWNetGround scalarSnowAlbedo scalarSurfaceTemp scalarGroundNetNrgFlux; do X="$X --extra $v"; done
$PY rerun_trials.py wolverine_added calibration 472 $X --forcing $PWD/wolverine_added/forcing/raingrad/ --label raingrad > $L/screen_wolverine_raingrad.log 2>&1 &
$PY rerun_trials.py gulkana_added calibration 468 $X --forcing $PWD/gulkana_added/forcing/raingrad/ --label raingrad > $L/screen_gulkana_raingrad.log 2>&1 &
$PY rerun_trials.py wolverine_general calibration 465 $X --label nrg > $L/screen_wolverine_general_nrg.log 2>&1 &
$PY rerun_trials.py gulkana_general calibration 392 $X --label nrg > $L/screen_gulkana_general_nrg.log 2>&1 &
wait
echo screen1 done
