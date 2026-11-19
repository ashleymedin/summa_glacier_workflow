#!/bin/bash
# Round 5b: all four cases rebuilt with glacier air cooling from Shaw et al. (2025) k (Gulkana added keeps Site B), firn
# viscosity from a 1 mm grain radius, debris domains uncooled (SUMMA df105e33) and the 0.002 m-1 snowfall gradient (general);
# spun up and calibrated, the added pair first.
cd "$(dirname "$0")/../../.."
PY=~/miniconda3/envs/glacier/bin/python
L=runs/logs/2026-11-19r5b
mkdir -p $L
export OMPI_MCA_mpi_yield_when_idle=1
$PY build_cases.py cases.yaml wolverine_added gulkana_added wolverine_general gulkana_general > $L/build.log 2>&1 || { echo "build failed"; exit 1; }
cd runs
for c in wolverine_added gulkana_added wolverine_general gulkana_general; do $PY spinup.py $c > logs/2026-11-19r5b/spinup_$c.log 2>&1 & done
wait
echo "rebuild done"
bash ../scratch/2026-11-19/paper1r5/run_r5b.sh "wolverine_added gulkana_added" "wolverine_general gulkana_general"
