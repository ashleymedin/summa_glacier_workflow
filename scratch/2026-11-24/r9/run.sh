#!/bin/bash
# Round 9: round 8's setup (seeds 42 and 43, merged fronts) with NSGA-II's first generation a Latin hypercube sample (summa
# 6e72e27e). Waits until no SUMMA run uses the binary, rebuilds it, keeps round 8 as calibration*_1123r8, then calibrates.
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
SUMMA=/Users/amedin/Research/SummaSundials/summa
L=logs/2026-11-24r9
mkdir -p $L
while pgrep -f "$SUMMA/bin/summa_sundials_mizuroute" > /dev/null || pgrep -f "r8/post_merge.py" > /dev/null; do sleep 120; done
echo "binary free $(date)"
(cd $SUMMA && env FC=/opt/local/bin/gfortran LIBRARY_LINKS='-llapack' SUNDIALS_DIR=/Users/amedin/Research/SummaSundials/sundials/instdir/ \
  cmake --build build/cmake_build_mizu --target all -j 8) > $L/build.log 2>&1 || { echo "build failed, see $L/build.log"; exit 1; }
echo "built $(date)"
for c in wolverine_general gulkana_general wolverine_added gulkana_added; do
  for d in calibration calibration_evaluation calibration_rerun calibration_s43 calibration_s43_evaluation calibration_s43_rerun; do
    [ -e $c/$d ] && mv $c/$d $c/${d}_1123r8
  done
done
export OMPI_MCA_mpi_yield_when_idle=1
for c in wolverine_general gulkana_general wolverine_added gulkana_added; do
  $PY ../scratch/2026-11-23/r8/post_merge.py $c 2026-11-24r9 calibration calibration_s43 > $L/post_driver_$c.log 2>&1 &
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
echo "round 9 done"
