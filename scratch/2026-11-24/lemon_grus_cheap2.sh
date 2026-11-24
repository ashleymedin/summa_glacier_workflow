#!/bin/bash
# lemon_grus rebuilt (Ptarmigan scored, small glaciers' room), spun up, then two cheap test calibrations as lemon_grus_cheap.sh on the SUMMA of branch gru-select:
# cheap_snow (snowfall multiplier of the northern glacier's and Ptarmigan's GRUs) and cheap_albedo (also the snow albedo of each GRU's glaciers)
cd "$(dirname "$0")/../.."
export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH SUMMA_DIR=$HOME/Research/SummaSundials/summa_grusel OMPI_MCA_mpi_yield_when_idle=1
python build_cases.py cases.yaml lemon_grus > runs/lemon_grus/build.log 2>&1 || exit 1
cd runs
python spinup.py lemon_grus > lemon_grus/spinup.log 2>&1 || exit 1
for n in snow:domain albedo:domain_gru; do
  python calibrate.py calibrate lemon_grus --search ${n#*:} --population 12 --generations 8 --ranks 3 --cal-end 2010-10-02 --name cheap_${n%:*} > lemon_grus/cheap_${n%:*}.log 2>&1 || echo failed >> lemon_grus/cheap_${n%:*}.log
done
