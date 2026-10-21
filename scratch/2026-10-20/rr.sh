#!/bin/zsh
# rr.sh <label> [rerun_trials options...]: trials 384 and 469 on the frozen build, in parallel
export SUMMA_DIR=${SUMMA_DIR:-/Users/amedin/Research/SummaSundials/summa_frozen_cal_03a797ed}
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs
py=~/miniconda3/envs/glacier/bin/python
lab=$1; shift
gargs=(); wargs=()
for x in "$@"; do
  case $x in G:*) gargs+=(${x#G:});; W:*) wargs+=(${x#W:});; *) gargs+=($x); wargs+=($x);; esac
done
$py rerun_trials.py gulkana_corrected calibration_paper1 384 --label $lab $gargs > gulkana_corrected/calibration_paper1_rerun/sample_384_$lab.log 2>&1 &
$py rerun_trials.py wolverine_corrected calibration_paper1 469 --label $lab $wargs > wolverine_corrected/calibration_paper1_rerun/sample_469_$lab.log 2>&1 &
wait
echo "$lab done"
