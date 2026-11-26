#!/bin/bash
# Lemon Creek calibrated as round 10 on the case the paired upland snow test chose (lemon_grus or lemon_grus_snow, the argument):
# 32 x 15, seeds 42 then 43, 4 ranks, on summa_r10, after lemon_pair_adv.sh exits; lemon_post.py merges the fronts and post-processes.
cd "$(dirname "$0")/../../runs"
C=${1:?case}; PY=/Users/amedin/miniconda3/envs/glacier/bin/python; L=logs/2026-11-26lemon_r10
export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH SUMMA_DIR=$HOME/Research/SummaSundials/summa_r10 OMPI_MCA_mpi_yield_when_idle=1
mkdir -p $L
while pgrep -f "lemon_pair_adv.sh" > /dev/null; do sleep 300; done
echo "start $C $(date)"
$PY ../scratch/2026-11-24/lemon_post.py $C 2026-11-26lemon_r10 calibration calibration_s43 > $L/post_driver.log 2>&1 &
for s in 42 43; do
  case $s in 42) n=calibration;; *) n=calibration_s$s;; esac
  $PY calibrate.py calibrate $C --search domain --population 32 --generations 15 --ranks 4 --seed $s --name $n \
    < /dev/null > $L/calibrate_${C}_$n.log 2>&1 || echo "$C $n calibration exited $?" | tee -a $L/calibrate_${C}_$n.log
done
wait
echo "lemon_r10 done $(date)"
