#!/bin/bash
# After screen3.sh: the general balanced trials with the lowest HRU's wind on every HRU (flat_wind_forcing.py).
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-18
export OMPI_MCA_mpi_yield_when_idle=1
until grep -q "screen3 done" $L/screen3.log 2>/dev/null; do sleep 60; done
X="--targets discharge,mass_balance,wgms_amce --aligned --ranks 2 --label flatwind"
for v in scalarSenHeatGround scalarLatHeatGround scalarGroundAbsorbedSolar scalarLWNetGround scalarGroundNetNrgFlux; do X="$X --extra $v"; done
$PY rerun_trials.py wolverine_general calibration 465 $X --forcing $PWD/wolverine_general/forcing/flatwind/ > $L/screen_wolverine_general_flatwind.log 2>&1 &
$PY rerun_trials.py gulkana_general calibration 392 $X --forcing $PWD/gulkana_general/forcing/flatwind/ > $L/screen_gulkana_general_flatwind.log 2>&1 &
wait
echo screen4 done
