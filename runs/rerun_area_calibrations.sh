#!/bin/tcsh -f
# calibrations rerun on the polygon HRU areas (d70e127), with the frozen 16 Oct calibration build
setenv SUMMA_DIR /Users/amedin/Research/SummaSundials/summa_frozen_cal_20261016
set py = ~/miniconda3/envs/modflow6/bin/python
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs
$py calibrate.py calibrate gulkana_corrected --population 32 --generations 15 --ranks 7 --name calibration_area >& gulkana_corrected_area.log || exit 1
$py calibrate.py evaluate  gulkana_corrected --ranks 2 --jobs 3 --name calibration_area >& gulkana_corrected_area_eval.log
foreach c (gulkana_raw wolverine_corrected wolverine_raw)
  $py calibrate.py calibrate $c --population 20 --generations 10 --ranks 7 --name pilot_area >& ${c}_pilot_area.log || continue
  $py calibrate.py evaluate  $c --ranks 2 --jobs 3 --name pilot_area >& ${c}_pilot_area_eval.log
end
