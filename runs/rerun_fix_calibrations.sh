#!/bin/tcsh -f
# calibrations on the polygon areas, gauge rain, Site B albedo bounds and the debris fix (summa dc8f8910, frozen)
setenv SUMMA_DIR /Users/amedin/Research/SummaSundials/summa_frozen_cal_debrisfix_dc8f8910
set py = ~/miniconda3/envs/modflow6/bin/python
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs
$py calibrate.py calibrate gulkana_corrected --population 32 --generations 15 --ranks 9 --name calibration_fix >& gulkana_corrected_fix.log || exit 1
$py calibrate.py evaluate  gulkana_corrected --ranks 2 --jobs 4 --name calibration_fix >& gulkana_corrected_fix_eval.log
foreach c (gulkana_raw wolverine_corrected wolverine_raw)
  $py calibrate.py calibrate $c --population 20 --generations 10 --ranks 9 --name pilot_fix >& ${c}_pilot_fix.log || continue
  $py calibrate.py evaluate  $c --ranks 2 --jobs 4 --name pilot_fix >& ${c}_pilot_fix_eval.log
end
