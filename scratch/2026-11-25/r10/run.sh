#!/bin/bash
# Round 10: round 9's setup (seeds 42 and 43, merged fronts) on summa's advective-heat code (built in summa_r10) with the upland
# snowfall rise (round10_upland_snow) in the added cases. Round 9 is kept as calibration*_1125r9. The added cases' inputs change only
# once stream_r9/run.sh has launched its search: its reruns pin round 9 trials and read cases.yaml.
cd "$(dirname "$0")/../../../runs"
export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH SUMMA_DIR=$HOME/Research/SummaSundials/summa_r10 OMPI_MCA_mpi_yield_when_idle=1
PY=/Users/amedin/miniconda3/envs/glacier/bin/python; L=logs/2026-11-25r10; mkdir -p $L; rm -f $L/ready_*
keep() {
  for d in calibration calibration_evaluation calibration_rerun calibration_s43 calibration_s43_evaluation calibration_s43_rerun; do
    [ -e $1/$d ] && { mv $1/$d $1/${d}_1125r9 || exit 1; }
  done; true
}
spin() { $PY spinup.py $1 > $L/spin_$1.log 2>&1 < /dev/null && { $PY ../scratch/2026-11-23/r8/post_merge.py $1 2026-11-25r10 calibration calibration_s43 > $L/post_driver_$1.log 2>&1 & touch $L/ready_$1; } || { echo "$1 spin-up failed"; touch $L/failed_$1; }; }
prep_added() {
  while pgrep -f "stream_r9/run.sh" > /dev/null && ! pgrep -f "calibrate.py calibrate wolverine_stream_delta.*stream_cheap_r9" > /dev/null; do sleep 30; done
  sleep 120 # the search has read its settings
  echo "stream_r9 reruns done $(date)"
  (cd .. && git apply scratch/2026-11-25/round10_upland_snow/cases.patch) || { touch $L/failed_wolverine_added $L/failed_gulkana_added; return; }
  for c in wolverine_added gulkana_added; do
    keep $c
    [ $c = wolverine_added ] && ln -sfn ../wolverine_added/calibration_1125r9 wolverine_stream_delta/calibration_r9
    [ $c = gulkana_added ] && ln -sfn ../gulkana_added/calibration_s43_1125r9 gulkana_stream/calibration_r9
    (cd .. && $PY build_cases.py cases.yaml $c) > $L/build_$c.log 2>&1 || { echo "$c build failed"; touch $L/failed_$c; continue; }
    spin $c
  done
}
calibrate() {
  while [ ! -e $L/ready_$1 ]; do [ -e $L/failed_$1 ] && return; sleep 20; done
  case $2 in 42) n=calibration;; *) n=calibration_s$2;; esac
  $PY calibrate.py calibrate $1 --search domain --population 32 --generations 15 --ranks 4 --seed $2 --name $n \
    < /dev/null > $L/calibrate_$1_$n.log 2>&1 || echo "calibration exited $?" >> $L/calibrate_$1_$n.log
}
export -f calibrate; export PY L
for c in wolverine_general gulkana_general; do keep $c; spin $c & done
prep_added &
printf "%s\n" "wolverine_general 42" "gulkana_general 42" "wolverine_general 43" "gulkana_general 43" \
  "wolverine_added 42" "gulkana_added 42" "wolverine_added 43" "gulkana_added 43" | xargs -P 3 -L 1 bash -c 'calibrate $0 $1'
wait
echo "round 10 done $(date)"
