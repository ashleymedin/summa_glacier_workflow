#!/bin/zsh
# The reach's friction heat from the fall between the modelled glacier front (lowest ice surface, basin__TerminusElev) and
# the gauge on the domain DEM (reachOutletElev 377 m Wolverine, 1137 m Gulkana), so it grows as the glacier retreats up
# its bed. Wolverine as the settling lake with fetch roughness, Gulkana as the fan whose area follows its flow.
# Needs SUMMA_DIR set to a build of wetland-area with reachOutletElev.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow --extra scalarWetlandFullArea --extra basin__TerminusElev)
$PY rerun_trials.py wolverine_stream calibration_added 459 $X --set wetlandSedConc=0.00075 --set wetlandSettleVel=0.00001 --set lakeFetch=200 --set reachOutletElev=377 --label front > ../scratch/2026-11-13/w_front.log 2>&1 &
$PY rerun_trials.py gulkana_stream calibration_added 451 $X --set wetlandMaxArea=40000 --set wetlandFlatArea=53000 --set reachOutletElev=1137 --label front > ../scratch/2026-11-13/g_front.log 2>&1 &
wait
