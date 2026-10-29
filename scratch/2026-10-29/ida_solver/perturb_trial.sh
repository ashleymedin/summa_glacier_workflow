#!/bin/bash
# Rerun a saved failed trial with k_soil scaled by each factor; usage: perturb_trial.sh <failed_trial_dir> <exe> <tag> <factor>...
d=$1; exe=$2; tag=$3; shift 3
for f in "$@"; do
  w=$d/pert_${tag}_$f; mkdir -p $w; cp $d/config.toml $d/initial_state.nc $d/rerun.sh $w/
  k=$(grep -o "k_soil [0-9.E+-]*" $d/rerun.sh | awk '{print $2}'); kn=$(python3 -c "print('%.16E' % ($k*$f))")
  sed -i '' "s/k_soil $k/k_soil $kn/" $w/rerun.sh
  (SUMMA_EXE=$exe bash $w/rerun.sh > /dev/null 2>&1; r=$(grep -c "does not balance\|FATAL ERROR" $w/rerun.log); echo "$tag $f fail=$r") &
done; wait
