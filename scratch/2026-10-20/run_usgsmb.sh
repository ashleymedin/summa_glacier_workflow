#!/bin/bash
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs
export SUMMA_DIR=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/2199a785-b91e-489f-9104-89726a74abf7/scratchpad/wt
P=~/miniconda3/envs/glacier/bin/python
D=/Users/amedin/Research/SummaSundials/summa_glacier_workflow/data
for A in 1 0.25; do
  $P rerun_trials.py gulkana_corrected calibration_paper1 384 --inputs gulkana_corrected/summa_inputs_flow --set glenAFactor=$A \
     --massbal $D/domain_Gulkana/observations/storage/mass_balance/gulkana_balance_profile.txt --label usgsmb_A$A > gulkana_corrected/calibration_paper1_rerun/sample_384_usgsmb_A$A.log 2>&1 &
  $P rerun_trials.py wolverine_corrected calibration_paper1 469 --inputs wolverine_corrected/summa_inputs_flow --set glenAFactor=$A \
     --massbal $D/domain_Wolverine/observations/storage/mass_balance/wolverine_balance_profile.txt --label usgsmb_A$A > wolverine_corrected/calibration_paper1_rerun/sample_469_usgsmb_A$A.log 2>&1 &
done
wait
