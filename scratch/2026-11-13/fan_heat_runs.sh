#!/bin/zsh
# Gulkana trial 451 (added-data calibration) rerun on the stream case over 2004-10 to 2026-09, bedrock layers off as
# calibrated: no wetland, the braided fan as built (1.4 km of threads wetting 40 m, 0.056 km2), and the whole fan
# wet (1.4 km by 150 m, 0.21 km2). Needs SUMMA_DIR set to a build with branch wetland-area.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow)
$PY rerun_trials.py gulkana_stream calibration_added 451 $X --inputs gulkana_stream/summa_inputs_nowet --label nowet > ../scratch/2026-11-13/g_nowet.log 2>&1 &
$PY rerun_trials.py gulkana_stream calibration_added 451 $X --label fan > ../scratch/2026-11-13/g_fan.log 2>&1 &
$PY rerun_trials.py gulkana_stream calibration_added 451 $X --inputs gulkana_stream/summa_inputs_wide --label wide > ../scratch/2026-11-13/g_wide.log 2>&1 &
wait
