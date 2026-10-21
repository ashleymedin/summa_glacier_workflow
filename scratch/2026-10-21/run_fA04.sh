#!/bin/bash
# Trials 384 and 469 at glenAFactor 0.4, on the USGS balance profiles and on SUMMA's own balance
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs
export SUMMA_DIR=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/58a1bdd5-537a-47c2-a041-064a4f12c97d/scratchpad/wt
P=~/miniconda3/envs/glacier/bin/python
D=/Users/amedin/Research/SummaSundials/summa_glacier_workflow/data
for g in "gulkana 384 Gulkana" "wolverine 469 Wolverine"; do
  set -- $g
  $P rerun_trials.py ${1}_corrected calibration_paper1 $2 --inputs ${1}_corrected/summa_inputs_flow2 --set glenAFactor=0.4 \
     --massbal $D/domain_$3/observations/storage/mass_balance/${1}_balance_profile.txt --label usgsmb2_A0.4 \
     > ${1}_corrected/calibration_paper1_rerun/sample_${2}_usgsmb2_A0.4.log 2>&1 &
  $P rerun_trials.py ${1}_corrected calibration_paper1 $2 --inputs ${1}_corrected/summa_inputs_flow2 --set glenAFactor=0.4 \
     --label flow2_A0.4 > ${1}_corrected/calibration_paper1_rerun/sample_${2}_flow2_A0.4.log 2>&1 &
done
wait
