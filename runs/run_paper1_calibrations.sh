#!/bin/tcsh -f
# glacier paper: discharge and mass balance, no stream HRU or wetland, on summa 3b904317 (frozen)
setenv SUMMA_DIR /Users/amedin/Research/SummaSundials/summa_frozen_cal_3b904317
set py = ~/miniconda3/envs/glacier/bin/python
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs
$py calibrate.py calibrate gulkana_corrected --population 32 --generations 15 --ranks 9 --name calibration_paper1 >& gulkana_corrected_paper1.log || exit 1
$py calibrate.py evaluate  gulkana_corrected --ranks 2 --jobs 4 --name calibration_paper1 >& gulkana_corrected_paper1_eval.log
foreach c (gulkana_raw wolverine_corrected wolverine_raw)
  $py calibrate.py calibrate $c --population 20 --generations 10 --ranks 9 --name pilot_paper1 >& ${c}_pilot_paper1.log || continue
  $py calibrate.py evaluate  $c --ranks 2 --jobs 4 --name pilot_paper1 >& ${c}_pilot_paper1_eval.log
end
