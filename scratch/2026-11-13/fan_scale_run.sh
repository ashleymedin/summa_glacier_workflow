#!/bin/zsh
# Gulkana trial 451 with the braided fan's wetted area following its flow, A^2 = A0^2 + 2 wetlandFlatArea K Q above the
# outlet, fitted to the Sentinel-2 wetted areas (gulkana_forefield.py: A = 0.045 Q^0.24 km2, 0.045 km2 at 1 m3/s and
# 0.086 at 15): A0 = wetlandMaxArea 40000 m2, wetlandFlatArea 53000 m2 per m with wetlandStorageK 3600 s.
# Needs SUMMA_DIR set to a build of wetland-area.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow)
$PY rerun_trials.py gulkana_stream calibration_added 451 $X --set wetlandMaxArea=40000 --set wetlandFlatArea=53000 --label scale > ../scratch/2026-11-13/g_scale.log 2>&1
