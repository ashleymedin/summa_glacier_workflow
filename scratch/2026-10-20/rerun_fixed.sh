#!/bin/bash
set -e
W=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/68ba93e3-bd37-4b3c-adc0-c5558bedf6d2/scratchpad/wt2
B="env FC=/opt/local/bin/gfortran LIBRARY_LINKS=-llapack SUNDIALS_DIR=/Users/amedin/Research/SummaSundials/sundials/instdir/"
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow
py=~/miniconda3/envs/glacier/bin/python
R=runs/gulkana_corrected/calibration_paper1_rerun
run() { $py runs/rerun_trials.py gulkana_corrected calibration_paper1 384 --set wallErosionRate=$2 --label $1; $py compare_glacier_change.py domains/gulkana.yaml $R/sample_384_$1; }
export SUMMA_DIR=$W
run slope40_e1 1
sed -i '' 's/wallMinSlope=40._rkind/wallMinSlope=35._rkind/' $W/build/source/engine/glacAreaChange.f90
$B cmake --build /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/68ba93e3-bd37-4b3c-adc0-c5558bedf6d2/scratchpad/build2 -j 2 > /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/68ba93e3-bd37-4b3c-adc0-c5558bedf6d2/scratchpad/build3.log
run slope35_e1 1
git -C $W checkout -- build/source/engine/glacAreaChange.f90
$B cmake --build /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/68ba93e3-bd37-4b3c-adc0-c5558bedf6d2/scratchpad/build2 -j 2 > /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/68ba93e3-bd37-4b3c-adc0-c5558bedf6d2/scratchpad/build3b.log
export SUMMA_DIR=/Users/amedin/Research/SummaSundials/summa_frozen_cal_3b904317
run wall1 1
run wall0.1 0.1
echo ALL DONE
