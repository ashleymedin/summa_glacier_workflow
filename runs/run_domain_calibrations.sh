#!/bin/tcsh -f
# glacier paper on the domain search (upland soil and debris apart, debrisConc searched), on summa 3f91e2b6 (frozen);
# starts once run_paper1_rest.sh is done; failed trials stay in <case>/<name>/output/failed_trials and are listed
setenv SUMMA_DIR /Users/amedin/Research/SummaSundials/summa_frozen_cal_3f91e2b6
set py = ~/miniconda3/envs/glacier/bin/python
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs
while (`ps -ax -o command | grep -c "run_paper1_rest.s[h]"` > 0)
  sleep 60
end
foreach run ("gulkana_corrected calibration_domain 32 15" "wolverine_corrected calibration_domain 32 15" \
             "gulkana_raw pilot_domain 20 10" "wolverine_raw pilot_domain 20 10")
  set r = ($run)
  $py ../domain_soil_params.py $r[1]/summa_inputs
  $py calibrate.py calibrate $r[1] --search domain --population $r[3] --generations $r[4] --ranks 9 --name $r[2] >& $r[1]_$r[2].log
  $py calibrate.py evaluate  $r[1] --ranks 2 --jobs 4 --name $r[2] >& $r[1]_$r[2]_eval.log
  set failed = $r[1]/$r[2]/output/failed_trials
  if (-d $failed) then
    echo "$r[1] $r[2]: `ls $failed | wc -l` failed trials" >> domain_failed_trials.log
    grep -h '"error"' $failed/*/trial.json | sed 's/.*summa_runPhysics\///' >> domain_failed_trials.log
  else
    echo "$r[1] $r[2]: no failed trials" >> domain_failed_trials.log
  endif
end
