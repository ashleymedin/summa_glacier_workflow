#!/bin/bash
# Round 8: 15 parameters (capillary retention 0.07, canopy wind 0.28, debris porosity 0.3 fixed), each case calibrated with seeds
# 42 (calibration) and 43 (calibration_s43), three calibrations at a time, general cases first; post_merge.py picks the balanced
# trial from each case's merged front once both seeds end. Round 6 kept as calibration*_1120r6.
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
D=../scratch/2026-11-23/r8
L=logs/2026-11-23r8
mkdir -p $L
export OMPI_MCA_mpi_yield_when_idle=1
for c in wolverine_general gulkana_general wolverine_added gulkana_added; do
  $PY $D/post_merge.py $c 2026-11-23r8 calibration calibration_s43 > $L/post_driver_$c.log 2>&1 &
done
calibrate() {
  case $2 in 42) n=calibration;; *) n=calibration_s$2;; esac
  $PY calibrate.py calibrate $1 --search domain --population 32 --generations 15 --ranks 4 --seed $2 --name $n \
    < /dev/null > $L/calibrate_$1_$n.log 2>&1 || echo "calibration exited $?" >> $L/calibrate_$1_$n.log
}
export -f calibrate; export PY L
printf "%s\n" "wolverine_general 42" "gulkana_general 42" "wolverine_general 43" "gulkana_general 43" \
  "wolverine_added 42" "gulkana_added 42" "wolverine_added 43" "gulkana_added 43" | xargs -P 3 -L 1 bash -c 'calibrate $0 $1'
wait
echo "round 8 done"
