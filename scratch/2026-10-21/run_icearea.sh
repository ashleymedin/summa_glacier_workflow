#!/bin/bash
# Trials 384 and 469 on the USGS balance profiles with glacier area from ice thickness (summa 8e1a1b9f on the mb-prescribed scratch base)
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs
export SUMMA_DIR=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/4ac083c7-0f61-4381-86ee-764f921e607f/scratchpad/wttest
P=~/miniconda3/envs/glacier/bin/python
D=/Users/amedin/Research/SummaSundials/summa_glacier_workflow/data
for A in 0.4 0.25; do
  for g in "gulkana 384 Gulkana" "wolverine 469 Wolverine"; do
    set -- $g
    $P rerun_trials.py ${1}_corrected calibration_paper1 $2 --inputs ${1}_corrected/summa_inputs_flow2 --set glenAFactor=$A \
       --massbal $D/domain_$3/observations/storage/mass_balance/${1}_balance_profile.txt --label usgsmb3_A$A \
       > ${1}_corrected/calibration_paper1_rerun/sample_${2}_usgsmb3_A$A.log 2>&1 &
  done
done
wait
