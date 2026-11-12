#!/bin/zsh
# Wolverine trial 459 with the filling lake, writing the lake's ice cover and layer ice, to see how its winter ice grows.
# Needs SUMMA_DIR set to a build of wetland-area at 1e4fab0a or later.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow --extra scalarWetlandFullArea
   --extra scalarLakeIceThick --extra mLayerVolFracIce --extra mLayerVolFracLiq --extra mLayerDepth)
$PY rerun_trials.py wolverine_stream calibration_added 459 $X --set wetlandSedConc=0.0000562 --label ice > ../scratch/2026-11-13/ice.log 2>&1
