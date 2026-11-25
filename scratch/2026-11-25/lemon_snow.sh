#!/bin/bash
# lemon_grus_snow (upland snowfall rising with elevation) built, spun up and cheaply calibrated (12 x 8, WY2006-22 windows of cases.yaml), then evaluated.
cd "$(dirname "$0")/../.."; export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH SUMMA_DIR=$HOME/Research/SummaSundials/summa_next OMPI_MCA_mpi_yield_when_idle=1
cd runs; L=logs/2026-11-25
python spinup.py lemon_grus_snow > $L/snow_spinup.log 2>&1 || exit 1
python calibrate.py calibrate lemon_grus_snow --search domain --population 12 --generations 8 --ranks 5 --name cheap_2006_22 < /dev/null > $L/snow_calibrate.log 2>&1 &&
python calibrate.py evaluate lemon_grus_snow --ranks 2 --jobs 3 --name cheap_2006_22 < /dev/null > $L/snow_evaluate.log 2>&1 || echo failed >> $L/snow_calibrate.log
echo "lemon_snow done $(date)"
