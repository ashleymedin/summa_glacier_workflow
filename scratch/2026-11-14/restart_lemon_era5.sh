#!/bin/bash
# Start the Lemon Creek ERA5 downloads at 01:00 once the Wolverine/Gulkana level downloads have exited.
cd "$(dirname "$0")/../.."
PY=/Users/amedin/miniconda3/envs/glacier/bin/python
LOG=data/domain_LemonCreek/forcing/logs
target=$(date -j -v+1d -f "%H:%M:%S" "01:00:00" +%s)
[ "$(date +%H)" -lt 1 ] && target=$(date -j -f "%H:%M:%S" "01:00:00" +%s)
while [ "$(date +%s)" -lt "$target" ]; do sleep 300; done
while pgrep -f "acquire_era5.*domains/wolverine.yaml" >/dev/null; do sleep 600; done
echo "start $(date)" >> $LOG/era5.log
$PY acquire_era5.py 2004-10 2026-09 domains/lemon_creek.yaml >> $LOG/era5.log 2>&1 &
$PY acquire_era5_levels.py 2004-10 2026-09 domains/lemon_creek.yaml >> $LOG/levels_ncar.log 2>&1 &
$PY acquire_era5_levels.py 2004-10 2026-09 domains/lemon_creek.yaml --source cds >> $LOG/levels_cds.log 2>&1 &
wait
echo "done $(date)" >> $LOG/era5.log
