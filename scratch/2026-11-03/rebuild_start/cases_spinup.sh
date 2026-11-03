#!/bin/bash
# Rebuild the four cases (dropping the stale coldState_cold.nc) and spin them up from the new cold states.
set -e
cd "$(dirname "$0")/../../.."
PY=~/miniconda3/envs/glacier/bin/python
for b in wolverine gulkana; do $PY run_study.py $b --steps cases spinup; done
