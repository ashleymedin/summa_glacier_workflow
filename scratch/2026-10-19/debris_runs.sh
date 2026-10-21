#!/bin/bash
set -e
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow
py=~/miniconda3/envs/glacier/bin/python
R=runs/gulkana_corrected/calibration_paper1_rerun
export SUMMA_DIR=/Users/amedin/Research/SummaSundials/summa_frozen_cal_3b904317
$py runs/rerun_trials.py gulkana_corrected calibration_paper1 384 --set wallErosionRate=0 --label wall0
$py compare_glacier_change.py domains/gulkana.yaml $R/sample_384_wall0
$py runs/rerun_trials.py gulkana_corrected calibration_paper1 384 --set wallErosionRate=0.1 --label wall0.1
$py compare_glacier_change.py domains/gulkana.yaml $R/sample_384_wall0.1
export SUMMA_DIR=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/68ba93e3-bd37-4b3c-adc0-c5558bedf6d2/scratchpad/wt
$py runs/rerun_trials.py gulkana_corrected calibration_paper1 384 --label nospread
$py compare_glacier_change.py domains/gulkana.yaml $R/sample_384_nospread
echo ALL DONE
