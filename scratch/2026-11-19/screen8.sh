#!/bin/bash
# Gulkana general's perennial upland snow (HRU 3), round-3 trial 418: the upland snowfall on the glacier's elevation shape,
# capped at x2 (the gauges' ratio to ERA5), or HRU 3's upland excess shed onto HRU 3's glacier (avalanching and drift).
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-19
S=../scratch/2026-11-19
export OMPI_MCA_mpi_yield_when_idle=1
X="--targets discharge,mass_balance,wgms_amce --aligned --ranks 2"
$PY rerun_trials.py gulkana_general calibration_1118r3_upmult 418 $X --inputs $S/inputs_gulkana_general_upshape --label upshape > $L/gulkana_general_upshape.log 2>&1 &
$PY rerun_trials.py gulkana_general calibration_1118r3 418 $X --pin frozenPrecipMultip@upland=2.0 --label upcap2 > $L/gulkana_general_upcap2.log 2>&1 &
wait
$PY rerun_trials.py gulkana_general calibration_1118r3_upmult 418 $X --inputs $S/inputs_gulkana_general_upshed --label upshed > $L/gulkana_general_upshed.log 2>&1
echo screen8 done
