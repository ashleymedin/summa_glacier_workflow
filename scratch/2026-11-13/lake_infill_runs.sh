#!/bin/zsh
# Wolverine trial 459 on the stream case with the lake filling with sediment at the concentration infill_fit.py fits
# to the imagery's 2020-2026 shrinking (m3 of deposit per m3 of glacier runoff).
# Needs SUMMA_DIR set to a build of wetland-area at 1e4fab0a or later, and wetlandSedConc in the case's localParamInfo.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow --extra scalarWetlandFullArea
   --extra scalarWetlandSediment --extra scalarWetlandFullDepth)
$PY rerun_trials.py wolverine_stream calibration_added 459 $X --set wetlandSedConc=0.0000562 --label infill > ../scratch/2026-11-13/infill.log 2>&1
