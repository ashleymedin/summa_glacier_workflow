#!/bin/bash
# Once every forcing month has its pressure levels (acquire_era5_levels.py, restarted here if it stops): the four
# domains' forcing again, the free air against the stations, the four cases rebuilt and spun up, and all four
# calibrated (32 x 15) with post_cal.py, the general pair first. The calibrations already there are kept as *_chelsa
# (general) and *_nov11 (added). Logs in runs/logs/2026-11-12/levels; "done" is written there at the end.
#
#     caffeinate -ims scratch/2026-11-11/overnight/deploy_levels.sh
cd "$(dirname "$0")/../../.."
PY=~/miniconda3/envs/glacier/bin/python
LOGS=runs/logs/2026-11-12/levels
CASES="wolverine_general gulkana_general wolverine_added gulkana_added"
ACQUIRE="acquire_era5_levels.py 2004-10 2026-09 domains/wolverine.yaml domains/gulkana.yaml"
mkdir -p $LOGS
say() { echo "$(date '+%m-%d %H:%M') $*" | tee -a $LOGS/deploy.log; }
have() { ls data/domain_$1/forcing/$2/*_ERA5_${3}_*.nc 2>/dev/null | wc -l | tr -d " "; }
# true while a domain lacks more than $1 months of levels
missing() { for d in Wolverine Gulkana; do [ $(( $(have $d raw_data merged) - $(have $d raw_levels levels) )) -gt $1 ] && return 0; done; return 1; }
all() { for p in "$@"; do wait $p || { say "failed: see $LOGS"; exit 1; }; done; }

while missing 0; do
  missing 1 && { pgrep -f "acquire_era5_levels.py.*--workers" > /dev/null || { say "NCAR download restarted"; $PY $ACQUIRE --workers 6 >> $LOGS/acquire_ncar.log 2>&1 & }; }  # NCAR lacks the newest month
  pgrep -f "acquire_era5_levels.py.*--source cds" > /dev/null || { say "CDS download restarted"; $PY $ACQUIRE --source cds --jobs 2 >> $LOGS/acquire_cds.log 2>&1 & }
  sleep 300
done
say "pressure levels complete"

pids=""
for d in wolverine gulkana wolverine_general gulkana_general; do
  $PY remap_forcing.py domains/$d.yaml > $LOGS/remap_$d.log 2>&1 & pids="$pids $!"
done
all $pids
pids=""
for d in wolverine gulkana; do
  $PY setup_glacier_domain.py domains/$d.yaml --steps forcing > $LOGS/forcing_$d.log 2>&1 & pids="$pids $!"
done
all $pids
say "forcing written"
$PY scratch/2026-11-11/levels/levels_vs_station.py > $LOGS/levels_vs_station.log 2>&1 &

$PY build_cases.py cases.yaml $CASES > $LOGS/build_cases.log 2>&1 || { say "build_cases failed"; exit 1; }
pids=""
for c in $CASES; do
  (cd runs && $PY spinup.py $c) > $LOGS/spinup_$c.log 2>&1 & pids="$pids $!"
done
all $pids
say "cases built and spun up"

for c in $CASES; do
  case $c in *_general) old=chelsa ;; *) old=nov11 ;; esac
  for f in calibration calibration_rerun calibration_evaluation; do
    [ -d runs/$c/$f ] && [ ! -e runs/$c/${f}_$old ] && mv runs/$c/$f runs/$c/${f}_$old
  done
done

cd runs
for pair in "wolverine_general gulkana_general" "wolverine_added gulkana_added"; do
  pids=""
  for c in $pair; do
    $PY calibrate.py calibrate $c --search domain --population 32 --generations 15 --ranks 4 --name calibration \
      > logs/2026-11-12/levels/calibrate_$c.log 2>&1 & pids="$pids $!"
    $PY ../scratch/2026-11-11/overnight/post_cal.py $c 2026-11-12/levels > logs/2026-11-12/levels/post_driver_$c.log 2>&1 &
  done
  wait $pids
  cd .. && say "calibrated: $pair" && cd runs
done
wait
cd .. && say "done" && touch $LOGS/done
