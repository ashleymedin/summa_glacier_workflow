#!/bin/bash
# After the paper-1 round-2 chain (run.sh) ends: the added-data balanced trials rerun with the glacier energy balance
# written, and two Wolverine sensitivity reruns, less warm air over the ice and brighter ice, all scored --aligned.
cd "$(dirname "$0")/../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-18
export OMPI_MCA_mpi_yield_when_idle=1
until grep -q "all done" $L/run.log 2>/dev/null; do sleep 120; done
X="--targets discharge,mass_balance,wgms_amce --aligned --ranks 2"
for v in scalarGlceMelt scalarSenHeatGround scalarLatHeatGround scalarGroundAbsorbedSolar scalarLWNetGround scalarSnowAlbedo scalarSurfaceTemp scalarGroundNetNrgFlux; do X="$X --extra $v"; done
$PY rerun_trials.py wolverine_added calibration 472 $X --label nrg > $L/nrg_wolverine.log 2>&1 &
$PY rerun_trials.py gulkana_added calibration 468 $X --label nrg > $L/nrg_gulkana.log 2>&1 &
$PY rerun_trials.py wolverine_added calibration 472 $X --set glacierTempReduction=0.6 --label cool06 > $L/nrg_wolverine_cool06.log 2>&1 &
$PY rerun_trials.py wolverine_added calibration 472 $X --set albedoFrznWatVisible=0.65 --set albedoFrznWatNearIR=0.4 --label ice065 > $L/nrg_wolverine_ice065.log 2>&1 &
wait
echo nrg done
