#!/bin/bash
# Round-4 Gulkana general trial 440 on the round-5b inputs with its upland snowfall multiplier capped at round 5's upper bound, 3.
cd "$(dirname "$0")/../../../runs"
export OMPI_MCA_mpi_yield_when_idle=1
~/miniconda3/envs/glacier/bin/python rerun_trials.py gulkana_general calibration_1119r4 440 --pin frozenPrecipMultip@upland=3 \
  --label r5binputs_mult3 --aligned --ranks 2
echo mult3 done
