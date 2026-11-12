#!/bin/zsh
# Wolverine trial 459 (added-data calibration) rerun on the stream case over 2004-10 to 2026-09, with the
# bedrock layers off as calibrated: no lake (wetlandMaxArea 0, it never opens), the lake from its volume, and the
# lake with a fetch-limited water roughness (z0Water 5e-5 m), and the lake sized to the imagery's Jul-Aug median
# since 2016 (0.034 km2, the bed's 0.84 m mean depth and stage as area to the 0.33 at that size). Needs SUMMA_DIR set to a build with branch wetland-area.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow --extra scalarWetlandFullArea)
$PY rerun_trials.py wolverine_stream calibration_added 459 $X --set wetlandMaxArea=0 --label nolake > ../scratch/2026-11-13/nolake.log 2>&1 &
$PY rerun_trials.py wolverine_stream calibration_added 459 $X --label lake > ../scratch/2026-11-13/lake.log 2>&1 &
$PY rerun_trials.py wolverine_stream calibration_added 459 $X --set z0Water=0.00005 --label lake_z0 > ../scratch/2026-11-13/lake_z0.log 2>&1 &
$PY rerun_trials.py wolverine_stream calibration_added 459 $X --set wetlandMaxArea=34000 --set wetlandMinDepth=0.84 --set wetlandShape=0.33 --label lake_med > ../scratch/2026-11-13/lake_med.log 2>&1 &
wait
