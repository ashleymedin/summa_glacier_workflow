#!/bin/bash
# Forcing again with the longwave from the basin's mean elevation (a9c3605), cases rebuilt, spun up and calibrated
# (32 x 15) with post_cal.py: the added pair at once, the general pair once the twin experiments (twin_all.sh), which
# read the general forcing, have finished. Old calibrations kept as *_nov11 (added) and calibration_partial1116
# (general, this morning's partial start). Logs in runs/logs/2026-11-16/lw.
#
#     caffeinate -ims scratch/2026-11-16/rerun_lw.sh
cd "$(dirname "$0")/../.." || exit 1
PY=/Users/amedin/miniconda3/envs/glacier/bin/python
LOGS=runs/logs/2026-11-16/lw
mkdir -p $LOGS
say() { echo "$(date '+%m-%d %H:%M') $*" | tee -a $LOGS/rerun.log; }
all() { for p in "$@"; do wait $p || { say "failed: see $LOGS"; exit 1; }; done; }

chain() {  # domains, cases, old-calibration suffix
  local doms=$1 cases=$2 old=$3 pids=""
  for d in $doms; do $PY remap_forcing.py domains/$d.yaml > $LOGS/remap_$d.log 2>&1 & pids="$pids $!"; done
  all $pids
  pids=""
  for d in $doms; do
    case $d in *_general) ;; *)
      F=data/domain_$(echo ${d:0:1} | tr a-z A-Z)${d:1}/forcing
      [ -d $F/SUMMA_input/station_corrected ] && mv $F/SUMMA_input/station_corrected $F/station_corrected_20261116
      $PY setup_glacier_domain.py domains/$d.yaml --steps forcing > $LOGS/forcing_$d.log 2>&1 & pids="$pids $!" ;;
    esac
  done
  all $pids
  say "forcing written: $doms"
  $PY build_cases.py cases.yaml $cases > $LOGS/build_cases_$old.log 2>&1 || { say "build_cases failed: $cases"; exit 1; }
  pids=""
  for c in $cases; do (cd runs && $PY spinup.py $c) > $LOGS/spinup_$c.log 2>&1 & pids="$pids $!"; done
  all $pids
  say "built and spun up: $cases"
  for c in $cases; do
    for f in calibration calibration_rerun calibration_evaluation; do
      [ -d runs/$c/$f ] && [ ! -e runs/$c/${f}_$old ] && mv runs/$c/$f runs/$c/${f}_$old
    done
  done
  pids=""
  for c in $cases; do
    (cd runs && $PY calibrate.py calibrate $c --search domain --population 32 --generations 15 --ranks 4 --name calibration) \
      > $LOGS/calibrate_$c.log 2>&1 & pids="$pids $!"
    (cd runs && $PY ../scratch/2026-11-11/overnight/post_cal.py $c 2026-11-16/lw) > $LOGS/post_driver_$c.log 2>&1 &
  done
  all $pids
  say "calibrated: $cases"
}

chain "wolverine gulkana" "wolverine_added gulkana_added" nov11 &
added=$!
while pgrep -f "twin_all.sh|twin.py" > /dev/null; do sleep 300; done
say "twin experiments finished"
chain "wolverine_general gulkana_general" "wolverine_general gulkana_general" partial1116 &
general=$!
wait $added $general
wait
say "done" && touch $LOGS/done
