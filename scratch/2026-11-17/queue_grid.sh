#!/bin/bash
# Grid twin on both general cases, Wolverine first; Gulkana's truth waits on its running twin_profile.py truth.
cd "$(dirname "$0")"
export OMPI_MCA_mpi_yield_when_idle=1
PY=/Users/amedin/miniconda3/envs/glacier/bin/python
$PY twin_grid.py run wolverine_general --jobs 5 > grid_wolverine_general.log 2>&1
$PY twin_grid.py report wolverine_general > grid_report_wolverine_general.txt 2>&1
while pgrep -f "twin_profile.py truth gulkana_general" > /dev/null; do sleep 30; done
$PY twin_grid.py run gulkana_general --jobs 5 > grid_gulkana_general.log 2>&1
$PY twin_grid.py report gulkana_general > grid_report_gulkana_general.txt 2>&1
