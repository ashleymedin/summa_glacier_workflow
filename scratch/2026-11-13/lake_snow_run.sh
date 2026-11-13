#!/bin/zsh
# Wolverine trial 459 on wolverine_stream_delta writing the lake's snow and ice budget each day: where the snow that lands
# on the lake ice goes (sublimation, melt drainage, the pond of snow without a layer) and the lake surface energy terms.
# Needs SUMMA_DIR set to a build of wetland-area.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
X=()
for v in scalarStreamTemp scalarStreamOutflow scalarStreamLatInflow scalarWetlandFullArea scalarLakeIceThick scalarSnowDepth \
         scalarGroundSublimation scalarSnowDrainage scalarSfcMeltPond nSnow scalarSurfaceTemp scalarSenHeatTotal \
         scalarLatHeatTotal scalarGroundNetNrgFlux airtemp windspd scalarGroundAbsorbedSolar \
         scalarLWNetGround; do X+=(--extra $v); done
$PY rerun_trials.py wolverine_stream_delta calibration_added 459 $X --label lakesnow > ../scratch/2026-11-13/w_lakesnow.log 2>&1
