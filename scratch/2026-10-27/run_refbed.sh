#!/bin/bash
# Trials 384 and 469 at glenAFactor 0.4 on the bed from Millan's reference survey, sampled once onto the flow grid, edges clamped; USGS balance and SUMMA's own
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs
export SUMMA_DIR=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/4ac083c7-0f61-4381-86ee-764f921e607f/scratchpad/wttest
P=~/miniconda3/envs/glacier/bin/python
D=/Users/amedin/Research/SummaSundials/summa_glacier_workflow/data
for g in "gulkana 384 Gulkana" "wolverine 469 Wolverine"; do
  set -- $g
  $P rerun_trials.py ${1}_corrected calibration_paper1 $2 --inputs ${1}_corrected/summa_inputs_flow4 --set glenAFactor=0.4 \
     --massbal $D/domain_$3/observations/storage/mass_balance/${1}_balance_profile.txt --label refbed_usgsmb_A0.4 \
     > ${1}_corrected/calibration_paper1_rerun/sample_${2}_refbed_usgsmb_A0.4.log 2>&1 &
  $P rerun_trials.py ${1}_corrected calibration_paper1 $2 --inputs ${1}_corrected/summa_inputs_flow4 --set glenAFactor=0.4 \
     --label refbed_A0.4 > ${1}_corrected/calibration_paper1_rerun/sample_${2}_refbed_A0.4.log 2>&1 &
done
wait
