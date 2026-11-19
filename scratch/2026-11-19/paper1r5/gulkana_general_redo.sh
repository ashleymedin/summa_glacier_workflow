#!/bin/bash
# Gulkana general rebuilt with the noise-based moraine trim, spun up and calibrated (its first round-5 calibration crashed when a
# rebuild rewrote its forcing).
cd "$(dirname "$0")/../../.."
PY=~/miniconda3/envs/glacier/bin/python
L=runs/logs/2026-11-19r5
export OMPI_MCA_mpi_yield_when_idle=1
$PY setup_glacier_domain.py domains/gulkana_general.yaml --steps rasters extend bands hrus vegetation zonal era5 coldstate > $L/setup_gulkana_general_redo.log 2>&1 || { echo "setup failed"; exit 1; }
$PY build_cases.py cases.yaml gulkana_general > $L/build_gulkana_general_redo.log 2>&1 || { echo "build failed"; exit 1; }
cd runs
$PY spinup.py gulkana_general > ../$L/spinup_gulkana_general_redo.log 2>&1 || { echo "spinup failed"; exit 1; }
echo "rebuild done"
$PY calibrate.py calibrate gulkana_general --search domain --population 32 --generations 15 --ranks 4 --name calibration \
  > logs/2026-11-19r5/calibrate_gulkana_general.log 2>&1 || echo "calibration exited $?" >> logs/2026-11-19r5/calibrate_gulkana_general.log
$PY ../scratch/2026-11-17/paper1/post_cal.py gulkana_general 2026-11-19r5 > logs/2026-11-19r5/post_driver_gulkana_general.log 2>&1
echo "done gulkana_general"
