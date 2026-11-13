#!/bin/zsh
# The reach falling from the front of the largest connected body of ice (basin__TerminusElev without ice cut off from
# the glacier), so Gulkana's stagnant debris-covered cells below its tongue no longer set the fall. Gulkana as the fan
# whose area follows its flow, Wolverine as the delta above the settling lake; compare sample_451_front and sample_459_delta.
# Needs SUMMA_DIR set to a build of wetland-area with the connected-body front.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow --extra scalarStreamLatInflowTemp
   --extra scalarWetlandFullArea --extra basin__TerminusElev)
$PY rerun_trials.py gulkana_stream calibration_added 451 $X --set wetlandMaxArea=40000 --set wetlandFlatArea=53000 --set reachOutletElev=1137 --label body > ../scratch/2026-11-13/g_body.log 2>&1 &
$PY rerun_trials.py wolverine_stream_delta calibration_added 459 $X --extra wetlandChainFlow --label body > ../scratch/2026-11-13/w_body.log 2>&1 &
wait
