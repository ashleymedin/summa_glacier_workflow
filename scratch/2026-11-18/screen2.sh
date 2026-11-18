#!/bin/bash
# After screen1.sh: the four balanced trials with fetch cooling along the flowline (katabatic-fetch rebased on multi-calib,
# worktree summa_katabatic), glacierCoolLength giving each setup's Site B cooling at Site B's 1640 m fetch.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-18
F=../scratch/2026-11-18/fetch
export OMPI_MCA_mpi_yield_when_idle=1
export SUMMA_DIR=/Users/amedin/Research/SummaSundials/summa_katabatic
until grep -q "screen1 done" $L/screen1.log 2>/dev/null; do sleep 60; done
X="--targets discharge,mass_balance,wgms_amce --aligned --ranks 2 --extra DOMfetch"
$PY rerun_trials.py wolverine_added calibration 472 $X --inputs $F/inputs_wolverine_added_L6952 --label fetch > $L/screen_wolverine_fetch.log 2>&1 &
$PY rerun_trials.py gulkana_added calibration 468 $X --inputs $F/inputs_gulkana_added_L6952 --label fetch > $L/screen_gulkana_fetch.log 2>&1 &
$PY rerun_trials.py wolverine_general calibration 465 $X --inputs $F/inputs_wolverine_general_L8164 --label fetch > $L/screen_wolverine_general_fetch.log 2>&1 &
$PY rerun_trials.py gulkana_general calibration 392 $X --inputs $F/inputs_gulkana_general_L8164 --label fetch > $L/screen_gulkana_general_fetch.log 2>&1 &
wait
echo screen2 done
