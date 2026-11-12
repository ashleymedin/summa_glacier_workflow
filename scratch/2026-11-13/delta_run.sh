#!/bin/zsh
# Wolverine trial 459 on wolverine_stream_delta: the braided delta as a wetland above the settling lake, taking the glacier
# runoff and draining to the lake once both open (wetlandFeedsNext), the reach falling from the modelled glacier front.
# Compare with sample_459_front of wolverine_stream, the same without the delta. Needs SUMMA_DIR set to a build of wetland-area.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow --extra scalarStreamLatInflowTemp
   --extra scalarWetlandFullArea --extra basin__TerminusElev --extra wetlandChainFlow)
$PY rerun_trials.py wolverine_stream_delta calibration_added 459 $X --label delta > ../scratch/2026-11-13/w_delta.log 2>&1
