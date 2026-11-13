#!/bin/zsh
# main_body_front_runs.sh on the inputs the earlier front and delta runs had: each case's summa_inputs copied with the
# attributes.nc of sample_451_front and sample_459_delta (before the WorldCover vegetation and mHeight of 13 Nov), so the
# connected-body front is the only change. Needs SUMMA_DIR set to a build of wetland-area with the connected-body front.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
for c s in gulkana_stream 451_front wolverine_stream_delta 459_delta; do
  rm -rf $c/summa_inputs_oldveg; cp -R $c/summa_inputs $c/summa_inputs_oldveg
  cp $c/calibration_added_rerun/sample_${s}_settings/attributes.nc $c/summa_inputs_oldveg/
done
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow --extra scalarStreamLatInflowTemp
   --extra scalarWetlandFullArea --extra basin__TerminusElev)
$PY rerun_trials.py gulkana_stream calibration_added 451 $X --set wetlandMaxArea=40000 --set wetlandFlatArea=53000 --set reachOutletElev=1137 \
    --inputs gulkana_stream/summa_inputs_oldveg --label body_oldveg > ../scratch/2026-11-13/g_body_oldveg.log 2>&1 &
$PY rerun_trials.py wolverine_stream_delta calibration_added 459 $X --extra wetlandChainFlow \
    --inputs wolverine_stream_delta/summa_inputs_oldveg --label body_oldveg > ../scratch/2026-11-13/w_body_oldveg.log 2>&1 &
wait
rm -rf gulkana_stream/summa_inputs_oldveg wolverine_stream_delta/summa_inputs_oldveg
