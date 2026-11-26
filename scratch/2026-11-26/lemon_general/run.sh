#!/bin/bash
# lemon_general_grus (lemon_general in lemon_grus's 3 GRUs; global data only, raw ERA5 with CHELSA) on the advective-heat code (summa_adv, fd892832):
# after round 10b (r10b/run.sh) ends, spun up, then the cheap search of the Lemon pair (12 x 8, seed 42, cheap_adv) and evaluated.
# The domain's settings were seeded from data/domain_LemonCreek's 1-GRU files; attributes.nc, coldState.nc and trialParams.nc were taken from
# data/domain_LemonCreek_grus (7 HRUs, global data only) and the hrus, vegetation, zonal and coldstate steps rerun on them.
cd "$(dirname "$0")/../../.."; S=$(cd ..; pwd); L=logs/2026-11-26lg; export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH SUMMA_DIR=$S/summa_adv OMPI_MCA_mpi_yield_when_idle=1
for p in "$@"; do while kill -0 $p 2>/dev/null; do sleep 120; done; done
echo "start $(date)"
cd runs
nice -n 5 python spinup.py lemon_general_grus > $L/spinup.log 2>&1 || { echo "spin-up failed $(date)"; exit 1; }
nice -n 5 python calibrate.py calibrate lemon_general_grus --search domain --population 12 --generations 8 --ranks 4 --seed 42 --name cheap_adv < /dev/null > $L/calibrate.log 2>&1 || { echo "calibration failed $(date)"; exit 1; }
nice -n 5 python calibrate.py evaluate lemon_general_grus --ranks 2 --jobs 2 --name cheap_adv < /dev/null > $L/evaluate.log 2>&1 || { echo "evaluation failed $(date)"; exit 1; }
echo "lemon_general_grus done $(date)"
