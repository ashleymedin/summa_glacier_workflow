#!/bin/bash
# Restart acquire_era5.py in the idle poll after a quarter is stored, so missing earlier months are requested next.
# usage: restart_after_quarter.sh <pid> <log> <last file of the quarter>
pid=$1; log=$2; last=$3
W=/Users/amedin/Research/SummaSundials/summa_glacier_workflow
until grep -q "wrote .*$last" "$log"; do kill -0 $pid 2>/dev/null || { echo "process $pid ended before $last"; exit 1; }; sleep 20; done
n=$(grep -n "wrote .*$last" "$log" | tail -1 | cut -d: -f1)
until tail -n +$n "$log" | grep -q -E "waiting:|submitted"; do sleep 2; done
if tail -n +$n "$log" | grep -q "submitted"; then echo "next quarter already submitted; not restarting"; exit 1; fi
kill $pid; sleep 5; pkill -f "caffeinate -i .*acquire_era5.py" 2>/dev/null
echo "$(date '+%F %T') stopped $pid after $last" | tee -a "$log"
(cd $W && nohup caffeinate -i /Users/amedin/miniconda3/envs/glacier/bin/python acquire_era5.py 2004-10 2026-09 domains/wolverine.yaml domains/gulkana.yaml --jobs 1 >> "$log" 2>&1 &)
sleep 60; grep "submitted" "$log" | tail -2; pgrep -f "python acquire_era5.py" >/dev/null && echo "restarted"
