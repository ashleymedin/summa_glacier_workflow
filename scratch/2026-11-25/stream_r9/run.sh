#!/bin/bash
# wolverine_stream_delta (rebuilt) spun up, round 9's balanced added-data trials (Wolverine 465, Gulkana seed 43's 413) rerun on the stream
# cases for Figs 2, 3 and 7 of glacier_forcing_runs.tex, then the cheap stream search pinned at Wolverine's 465, with its wetland profile.
cd "$(dirname "$0")/../../../runs"; export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH SUMMA_DIR=$HOME/Research/SummaSundials/summa_next OMPI_MCA_mpi_yield_when_idle=1
S=../scratch/2026-11-25/stream_r9; L=logs/2026-11-25/stream_r9; mkdir -p $L
step() { n=$1; shift; echo "$(date +%H:%M) $n"; "$@" < /dev/null > $L/$n.log 2>&1 || { echo "$n failed"; return 1; }; }
step spin_delta python spinup.py wolverine_stream_delta || exit 1
step build_variants python $S/variants.py build && for v in wolverine_stream_lake gulkana_stream_fan gulkana_stream_nowet; do step spin_$v python $S/variants.py spin $v || exit 1; done
ln -sfn ../gulkana_added/calibration_s43 gulkana_stream/calibration_r9
X="--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow"
w() { l=$1; shift; step w_$l python rerun_trials.py wolverine_stream_delta calibration_r9 465 $X --label $l "$@"; }
g() { l=$1; shift; step g_$l python rerun_trials.py gulkana_stream calibration_r9 413 $X --label $l "$@"; }
K="--inputs wolverine_stream_lake/summa_inputs"
w delta
w nolake $K --set wetlandMaxArea=0
w fetch $K
w settle $K --set lakeFetch=0
w lake $K --set lakeFetch=0 --set wetlandSedConc=0
w infill $K --set lakeFetch=0 --set wetlandSedConc=0.0000562 --set wetlandSettleVel=1.0
g nowet --inputs gulkana_stream_nowet/summa_inputs
g fan --inputs gulkana_stream_fan/summa_inputs
g scale --inputs gulkana_stream_fan/summa_inputs --set wetlandMaxArea=40000 --set wetlandFlatArea=53000
echo "$(date +%H:%M) reruns done"
$S/../../2026-11-24/white_ice_merge/profile_wetland.sh "wolverine_stream_delta/stream_cheap_r9" $S/prof 600 20 > $L/profile.log 2>&1 &
step stream_cheap_r9 python calibrate.py calibrate wolverine_stream_delta --search stream --population 12 --generations 8 --ranks 3 --pin-trial calibration_r9:465 --name stream_cheap_r9
echo "$(date +%H:%M) search done"
