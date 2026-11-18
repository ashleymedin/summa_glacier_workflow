#!/bin/bash
# After screen8.sh: the round-3 trials with the upland soil fixed by its SoilGrids texture class (Carsel and Parrish 1988;
# soilgrids_texture.py): Wolverine sandy loam, Gulkana loam; macropores and everything else as calibrated.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-19
S=../scratch/2026-11-19
export OMPI_MCA_mpi_yield_when_idle=1
until grep -q "screen8 done" $L/screen8.log 2>/dev/null; do sleep 60; done
X="--targets discharge,mass_balance,wgms_amce --aligned --ranks 2 --label soilgrids"
W="--pin k_soil@upland=1.23e-5 --pin theta_sat@upland=0.41 --pin theta_res@upland=0.065 --pin vGn_n@upland=1.89 --pin frac_sand@upland=0.54"
G="--pin k_soil@upland=2.89e-6 --pin theta_sat@upland=0.43 --pin theta_res@upland=0.078 --pin vGn_n@upland=1.56 --pin frac_sand@upland=0.49"
$PY rerun_trials.py wolverine_added calibration_1118r3 405 $X $W --inputs $S/inputs_wolverine_added_soilgrids > $L/wolverine_added_soilgrids.log 2>&1 &
$PY rerun_trials.py gulkana_added calibration_1118r3 467 $X $G --inputs $S/inputs_gulkana_added_soilgrids > $L/gulkana_added_soilgrids.log 2>&1 &
wait
$PY rerun_trials.py wolverine_general calibration_1118r3 452 $X $W --inputs $S/inputs_wolverine_general_soilgrids > $L/wolverine_general_soilgrids.log 2>&1 &
$PY rerun_trials.py gulkana_general calibration_1118r3 418 $X $G --inputs $S/inputs_gulkana_general_soilgrids > $L/gulkana_general_soilgrids.log 2>&1 &
wait
echo screen9 done
