#!/bin/bash
# Cheap lemon_grus calibrations (12 x 8, per-GRU snowfall), run from WY2006 and scored on WY2018-22, 2013-22 and 2006-22, each front then scored on WY2023-26;
# lemon_stream_grus rebuilt and spun up, then a stream search pinned at cheap_snow's balanced trial. SUMMA multi-calib bf5ddb11 (summa_next).
cd "$(dirname "$0")/../../../runs"
export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH SUMMA_DIR=$HOME/Research/SummaSundials/summa_next OMPI_MCA_mpi_yield_when_idle=1
L=logs/2026-11-24night; mkdir -p $L
cal() {  # name, score start
  nice -n 5 python calibrate.py calibrate lemon_grus --search domain --population 12 --generations 8 --ranks 3 --score-start $2 --name $1 < /dev/null > $L/$1.log 2>&1 &&
  nice -n 5 python calibrate.py evaluate lemon_grus --ranks 2 --jobs 2 --name $1 < /dev/null > $L/$1_evaluate.log 2>&1 || echo "failed $1" >> $L/$1.log
}
stream() {
  (cd .. && python build_cases.py cases.yaml lemon_stream_grus) > $L/stream_build.log 2>&1 && python spinup.py lemon_stream_grus > $L/stream_spinup.log 2>&1 || { echo failed >> $L/stream_spinup.log; return; }
  while ! ls lemon_grus/cheap_snow/output/*_calibration.nc > /dev/null 2>&1 || pgrep -f "name cheap_snow" > /dev/null; do sleep 120; done
  t=$(python ../scratch/2026-11-24/lemon_night/pick.py lemon_grus/cheap_snow) || return
  nice -n 5 python calibrate.py calibrate lemon_stream_grus --search stream --population 12 --generations 8 --ranks 3 --pin-trial calibration_pin:$t --name stream_cheap < /dev/null > $L/stream_cheap.log 2>&1 || echo failed >> $L/stream_cheap.log
}
(cal score_2018_22 2017-10-01; cal score_2013_22 2012-10-01) &
cal score_2006_22 2005-10-01 &
stream &
wait
echo "night done $(date)"
