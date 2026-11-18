#!/bin/bash
# Round-3 balanced trials screened for the open problems: a weaker stable-air turbulence over the ice (Mahrt87_eScale 2) for the
# warm-summer melt, Wolverine added's glacier snowfall raised to its stakes' winter balance (HRU 2 x1.20, HRU 3 x1.11), and
# Gulkana general's debris concentration fixed (1.28, Gulkana added's; 0.5).
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-19
export OMPI_MCA_mpi_yield_when_idle=1
X="--targets discharge,mass_balance,wgms_amce --aligned --ranks 2"
for v in scalarSenHeatGround scalarLatHeatGround scalarGroundAbsorbedSolar scalarLWNetGround scalarGroundNetNrgFlux; do X="$X --extra $v"; done
$PY rerun_trials.py wolverine_added calibration 405 $X --set Mahrt87_eScale=2 --label mahrt2 > $L/wolverine_added_mahrt2.log 2>&1 &
$PY rerun_trials.py wolverine_general calibration 452 $X --set Mahrt87_eScale=2 --label mahrt2 > $L/wolverine_general_mahrt2.log 2>&1 &
$PY rerun_trials.py gulkana_added calibration 467 $X --set Mahrt87_eScale=2 --label mahrt2 > $L/gulkana_added_mahrt2.log 2>&1 &
$PY rerun_trials.py gulkana_general calibration 418 $X --pin debrisConc=1.28 --label debris128 > $L/gulkana_general_debris128.log 2>&1 &
wait
$PY rerun_trials.py wolverine_added calibration 405 $X --inputs ../scratch/2026-11-19/inputs_wolverine_added_snowfix --label snowfix > $L/wolverine_added_snowfix.log 2>&1 &
$PY rerun_trials.py gulkana_general calibration 418 $X --pin debrisConc=0.5 --label debris05 > $L/gulkana_general_debris05.log 2>&1 &
$PY rerun_trials.py gulkana_general calibration 418 $X --set Mahrt87_eScale=2 --label mahrt2 > $L/gulkana_general_mahrt2.log 2>&1 &
wait
echo screen6 done
