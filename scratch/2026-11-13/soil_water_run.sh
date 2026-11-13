#!/bin/zsh
# Wolverine trial 459 on wolverine_stream_delta writing each domain's runoff by path (surface runoff, soil column outflow
# by layer, soil drainage) and the layer temperatures, to find which path carries the warm October-November water.
# Needs SUMMA_DIR set to a build of wetland-area.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
X=()
for v in scalarStreamTemp scalarStreamOutflow scalarStreamLatInflow scalarStreamLatInflowTemp scalarSurfaceRunoff \
         mLayerColumnOutflow scalarSoilDrainage scalarAquiferBaseflow mLayerTemp mLayerDepth scalarSurfaceTemp; do X+=(--extra $v); done
$PY rerun_trials.py wolverine_stream_delta calibration_added 459 $X --label soilwater > ../scratch/2026-11-13/w_soilwater.log 2>&1
