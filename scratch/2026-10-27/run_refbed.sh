#!/bin/bash
# Trials 384 and 469 at glenAFactor 0.4 on the bed from Millan's reference survey, sampled once onto the flow grid, edges clamped; USGS balance and SUMMA's own
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs
export SUMMA_DIR=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/9d44fcc9-c97e-47bd-8aaf-d13e79e5cd25/scratchpad/wtref  # summa 9cdc52ab + glacier-ice-area 8e1a1b9f
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
$P rerun_trials.py gulkana_corrected calibration_paper1 384 --inputs gulkana_corrected/summa_inputs_flow3 --set glenAFactor=0.4 --massbal $D/domain_Gulkana/observations/storage/mass_balance/gulkana_balance_profile.txt --label meltout_usgsmb_A0.4_check > gulkana_corrected/calibration_paper1_rerun/sample_384_meltout_usgsmb_A0.4_check.log 2>&1 &  # the same build reproduces the melt-out run
wait
