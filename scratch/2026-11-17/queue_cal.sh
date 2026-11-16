#!/bin/bash
# After the screens: calibrate both general setups with the rain-snow split searched, then sweep each parameter from the compromise.
cd "$(dirname "$0")"
export OMPI_MCA_mpi_yield_when_idle=1
PY=/Users/amedin/miniconda3/envs/glacier/bin/python
while pgrep -f queue_screen.sh > /dev/null; do sleep 60; done
for c in wolverine_general gulkana_general; do
  $PY oat.py calibrate $c --ranks 10 > cal_phase_$c.log 2>&1 || continue
  $PY oat.py sweep $c --jobs 9 > oat_$c.log 2>&1
  $PY oat.py report $c > oat_report_$c.txt 2>&1
done
