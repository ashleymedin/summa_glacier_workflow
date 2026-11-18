#!/bin/bash
# screen9's failed SoilGrids reruns again: Wolverine's water contents spaced by the search's least gap (sandy loam's curve is too
# flat between wilting and field capacity), Gulkana general on the rebuilt (trimmed) case with debris 0.44 like its trim rerun.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-19
S=../scratch/2026-11-19
export OMPI_MCA_mpi_yield_when_idle=1
X="--targets discharge,mass_balance,wgms_amce --aligned --ranks 2 --label soilgrids"
W="--pin k_soil@upland=1.23e-5 --pin theta_sat@upland=0.41 --pin theta_res@upland=0.065 --pin vGn_n@upland=1.89 --pin frac_sand@upland=0.54 --pin critSoilWilting@upland=0.076 --pin critSoilTranspire@upland=0.087 --pin fieldCapacity@upland=0.098"
G="--pin k_soil@upland=2.89e-6 --pin theta_sat@upland=0.43 --pin theta_res@upland=0.078 --pin vGn_n@upland=1.56 --pin frac_sand@upland=0.49 --pin critSoilWilting@upland=0.088 --pin critSoilTranspire@upland=0.127 --pin fieldCapacity@upland=0.165"
$PY rerun_trials.py wolverine_added calibration_1118r3 405 $X $W --inputs $S/inputs_wolverine_added_soilgrids > $L/wolverine_added_soilgrids.log 2>&1 &
$PY rerun_trials.py wolverine_general calibration_1118r3 452 $X $W --inputs $S/inputs_wolverine_general_soilgrids > $L/wolverine_general_soilgrids.log 2>&1 &
wait
rm -rf $S/inputs_gulkana_general_soilgrids && $PY $S/valley_air_inputs.py gulkana_general $S/inputs_gulkana_general_soilgrids > /dev/null
$PY - <<'PY'
import netCDF4 as nc, numpy as np
p = "../scratch/2026-11-19/inputs_gulkana_general_soilgrids"
typ = np.ma.filled(nc.Dataset(f"{p}/coldState.nc")["domType"][:], -1).T
with nc.Dataset(f"{p}/trialParams.nc", "a") as d:
    x = np.array(d["vGn_alpha"][:]); x[(typ == 1) | (typ == 3)] = -3.6; d["vGn_alpha"][:] = x
PY
$PY rerun_trials.py gulkana_general calibration_1118r3 418 $X $G --pin debrisConc=0.44 --inputs $S/inputs_gulkana_general_soilgrids > $L/gulkana_general_soilgrids.log 2>&1
echo screen10 done
