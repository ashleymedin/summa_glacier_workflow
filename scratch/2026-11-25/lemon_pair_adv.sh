#!/bin/bash
# After round 10 (r10/run.sh) and lemon_rescore.sh end: lemon_grus rebuilt and spun up on fd892832 (summa_adv; old inputs kept as summa_inputs_bf5ddb11), then lemon_grus and
# lemon_grus_snow (already spun up by lemon_adv.sh) calibrated on it with the same cheap search (12 x 8, seed 42) and evaluated: the paired test of the upland snow rise.
cd "$(dirname "$0")/../.."; W=$PWD; S=$(cd ..; pwd); L=logs/2026-11-25; export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH SUMMA_DIR=$S/summa_adv OMPI_MCA_mpi_yield_when_idle=1
for p in "$@"; do while kill -0 $p 2>/dev/null; do sleep 120; done; done
echo "start $(date)"
[ -e runs/lemon_grus/summa_inputs_bf5ddb11 ] || cp -Rp runs/lemon_grus/summa_inputs runs/lemon_grus/summa_inputs_bf5ddb11
nice -n 5 python build_cases.py cases.yaml lemon_grus > runs/$L/pair_build.log 2>&1 || { echo "case build failed"; exit 1; }
diff -rq runs/lemon_grus/summa_inputs runs/lemon_grus/summa_inputs_bf5ddb11
cd runs; nice -n 5 python spinup.py lemon_grus > $L/pair_spinup.log 2>&1 || { echo "spin-up failed"; exit 1; }
for c in lemon_grus lemon_grus_snow; do
  { nice -n 5 python calibrate.py calibrate $c --search domain --population 12 --generations 8 --ranks 4 --seed 42 --name cheap_adv < /dev/null > $L/pair_calibrate_$c.log 2>&1 &&
    nice -n 5 python calibrate.py evaluate $c --ranks 2 --jobs 2 --name cheap_adv < /dev/null > $L/pair_evaluate_$c.log 2>&1 && echo "$c ok $(date)" || echo "$c failed $(date)"; } &
done; wait
echo "lemon_pair_adv done $(date)"
