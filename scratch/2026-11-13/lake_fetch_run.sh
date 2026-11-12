#!/bin/zsh
# Wolverine trial 459 with the settling lake and its open-water roughness from wind, fetch (200 m, the lake's long axis
# down-valley) and depth instead of the fixed z0Water. Needs SUMMA_DIR set to a build of wetland-area with lakeFetch.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow --extra scalarWetlandFullArea
   --extra scalarSenHeatGround --extra scalarLatHeatGround --extra scalarGroundAbsorbedSolar --extra scalarLWNetGround)
$PY rerun_trials.py wolverine_stream calibration_added 459 $X --set wetlandSedConc=0.00075 --set wetlandSettleVel=0.00001 --set lakeFetch=200 --label fetch > ../scratch/2026-11-13/fetch.log 2>&1
