#!/bin/bash
# Wolverine balanced trials with one of the fix3 values at a time: capillary retention 0.06 (label fcap), canopy wind 0.28 (label wind).
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-23fix3
export OMPI_MCA_mpi_yield_when_idle=1
for spec in "wolverine_general calibration 473" "wolverine_added calibration_1120r5b 465"; do
  set -- $spec
  $PY rerun_trials.py $1 $2 $3 --calibration-years --ranks 2 --pin Fcapil=0.06 --label fcap < /dev/null > $L/${1}_${2}_fcap.log 2>&1 &
  $PY rerun_trials.py $1 $2 $3 --calibration-years --ranks 2 --pin windReductionParam=0.28 --label wind < /dev/null > $L/${1}_${2}_wind.log 2>&1 &
done
wait
echo "split done"
