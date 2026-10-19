#!/bin/tcsh -f
# glacier paper, after Gulkana corrected: Wolverine corrected gets the full search, the raw runs pilots
setenv SUMMA_DIR /Users/amedin/Research/SummaSundials/summa_frozen_cal_3b904317
set py = ~/miniconda3/envs/glacier/bin/python
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs
while (`ps -ax -o command | grep -c "^$py calibrate.py calibrate gulkana_raw"` > 0)
  sleep 60
end
$py calibrate.py evaluate  gulkana_raw --ranks 2 --jobs 4 --name pilot_paper1 >& gulkana_raw_pilot_paper1_eval.log
$py calibrate.py calibrate wolverine_corrected --population 32 --generations 15 --ranks 9 --name calibration_paper1 >& wolverine_corrected_paper1.log
$py calibrate.py evaluate  wolverine_corrected --ranks 2 --jobs 4 --name calibration_paper1 >& wolverine_corrected_paper1_eval.log
$py calibrate.py calibrate wolverine_raw --population 20 --generations 10 --ranks 9 --name pilot_paper1 >& wolverine_raw_pilot_paper1.log
$py calibrate.py evaluate  wolverine_raw --ranks 2 --jobs 4 --name pilot_paper1 >& wolverine_raw_pilot_paper1_eval.log
