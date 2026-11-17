#!/bin/bash
# Real-data split test on both general cases, Wolverine first; Gulkana's waits on its calibration and sweep.
cd "$(dirname "$0")"
export OMPI_MCA_mpi_yield_when_idle=1
PY=/Users/amedin/miniconda3/envs/glacier/bin/python
$PY split_grid.py run wolverine_general --jobs 4 > split_wolverine_general.log 2>&1
$PY split_grid.py report wolverine_general > split_report_wolverine_general.txt 2>&1
until [ -f oat_report_gulkana_general.txt ]; do sleep 60; done
$PY split_grid.py run gulkana_general --jobs 6 > split_gulkana_general.log 2>&1
$PY split_grid.py report gulkana_general > split_report_gulkana_general.txt 2>&1
