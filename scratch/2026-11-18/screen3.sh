#!/bin/bash
# After screen2.sh: the four balanced trials with melting snow's minimum albedo at Site B's 2024 melt-season plateau
# (albedoMinSpring 0.65 for the default 0.55; sw_vs_siteB.py, Wilson et al. daily albedo).
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-18
export OMPI_MCA_mpi_yield_when_idle=1
until grep -q "screen2 done" $L/screen2.log 2>/dev/null; do sleep 60; done
X="--targets discharge,mass_balance,wgms_amce --aligned --ranks 2 --set albedoMinSpring=0.65 --label albmin065 --extra scalarSnowAlbedo"
$PY rerun_trials.py wolverine_added calibration 472 $X > $L/screen_wolverine_albmin.log 2>&1 &
$PY rerun_trials.py gulkana_added calibration 468 $X > $L/screen_gulkana_albmin.log 2>&1 &
$PY rerun_trials.py wolverine_general calibration 465 $X > $L/screen_wolverine_general_albmin.log 2>&1 &
$PY rerun_trials.py gulkana_general calibration 392 $X > $L/screen_gulkana_general_albmin.log 2>&1 &
wait
echo screen3 done
