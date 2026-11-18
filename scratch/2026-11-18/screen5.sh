#!/bin/bash
# The added-data balanced trials with both the rain gradient (rain_gradient_forcing.py) and Site B's melting-snow albedo floor.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-18
export OMPI_MCA_mpi_yield_when_idle=1
X="--targets discharge,mass_balance,wgms_amce --aligned --ranks 2 --set albedoMinSpring=0.65 --label rain_alb"
$PY rerun_trials.py wolverine_added calibration 472 $X --forcing $PWD/wolverine_added/forcing/raingrad/ > $L/screen_wolverine_rain_alb.log 2>&1 &
$PY rerun_trials.py gulkana_added calibration 468 $X --forcing $PWD/gulkana_added/forcing/raingrad/ > $L/screen_gulkana_rain_alb.log 2>&1 &
wait
echo screen5 done
