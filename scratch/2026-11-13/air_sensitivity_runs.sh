#!/bin/zsh
# Sensitivity of the wetland's heat to the air it sees, the HRU's air and wind being the default: half the wind
# (sheltering by the moraines and valley walls, wetlandWindFactor 0.5) and the glacier's full katabatic cooling of air
# above freezing (air drained off the ice, wetlandAirCooling 1). Wolverine as the settling lake with fetch roughness,
# Gulkana as the fan whose area follows its flow. Needs SUMMA_DIR set to a build of wetland-area with these parameters.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow --extra scalarWetlandFullArea)
WL=(--set wetlandSedConc=0.00075 --set wetlandSettleVel=0.00001 --set lakeFetch=200)
GF=(--set wetlandMaxArea=40000 --set wetlandFlatArea=53000)
$PY rerun_trials.py wolverine_stream calibration_added 459 $X $WL --set wetlandWindFactor=0.5 --label wind05 > ../scratch/2026-11-13/w_wind05.log 2>&1 &
$PY rerun_trials.py wolverine_stream calibration_added 459 $X $WL --set wetlandAirCooling=1 --label cool1 > ../scratch/2026-11-13/w_cool1.log 2>&1 &
$PY rerun_trials.py gulkana_stream calibration_added 451 $X $GF --set wetlandWindFactor=0.5 --label wind05 > ../scratch/2026-11-13/g_wind05.log 2>&1 &
$PY rerun_trials.py gulkana_stream calibration_added 451 $X $GF --set wetlandAirCooling=1 --label cool1 > ../scratch/2026-11-13/g_cool1.log 2>&1 &
wait
