#!/bin/bash
# Cheap test calibration of lemon_grus (flat snowfall above the highest stake, Hugonnet target on the northern glacier) on the white-ice
# SUMMA: WY2006-2010 (to 2 Oct, so the WY2010 Hugonnet mean counts), 12 x 8 trials, 3 ranks; waits for the default run with the same inputs (its spin-up makes the cold state)
cd "$(dirname "$0")/../../runs"
export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH SUMMA_DIR=$HOME/Research/SummaSundials/summa_wetprecip OMPI_MCA_mpi_yield_when_idle=1
until grep -q "FORTRAN STOP" lemon_grus/test/flat/run.log 2>/dev/null; do sleep 10; done
python calibrate.py calibrate lemon_grus --search domain --population 12 --generations 8 --ranks 3 --cal-end 2010-10-02 --name cheap
