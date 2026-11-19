#!/bin/bash
# After rebuild.sh: round-4 general balanced trials rerun on the slowed melt-out bed, not recalibrated: yearly glacier grids
# for the area, and the aligned scores.
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-19r5
export OMPI_MCA_mpi_yield_when_idle=1
until grep -q "rebuild done" $L/rebuild.log 2>/dev/null; do sleep 60; done
for c in gulkana_general:440 wolverine_general:465; do
  case=${c%%:*}; s=${c##*:}
  ( $PY rerun_trials.py $case calibration_1119r4 $s --ranks 1 --label slowed > $L/screen_${case}_slowed.log 2>&1
    $PY ../compare_glacier_change.py ../domains/$case.yaml $case/calibration_1119r4_rerun/sample_${s}_slowed > $L/area_${case}_slowed.log 2>&1 ) &
  $PY rerun_trials.py $case calibration_1119r4 $s --targets discharge,wgms_amce --aligned --ranks 1 --label slowed_aligned > $L/screen_${case}_slowed_aligned.log 2>&1 &
done
wait
echo screen done
