#!/bin/zsh
# Wolverine trial 459 with the lake trapping the share of its inflow's sediment that settles (fine silt, 1e-5 m/s) at a
# concentration of 7.5e-4 m3 of deposit per m3 of glacier runoff, both fitted to the Jul-Aug imagery since 2013 (infill_fit.py).
# Needs SUMMA_DIR set to a build of wetland-area with wetlandSettleVel.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow --extra scalarWetlandFullArea
   --extra scalarWetlandSediment --extra scalarLakeIceThick)
$PY rerun_trials.py wolverine_stream calibration_added 459 $X --set wetlandSedConc=0.00075 --set wetlandSettleVel=0.00001 --label settle > ../scratch/2026-11-13/settle.log 2>&1
