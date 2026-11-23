#!/bin/bash
# Balanced trials rerun over the calibration years with the canopy wind reduction at SUMMA's default (0.28), the snow's capillary
# retention at SUMMA's default (0.06) and the debris porosity at DebDaB's usual 0.3 (label fix3), and as found (label asis).
cd "$(dirname "$0")/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
L=logs/2026-11-23fix3
mkdir -p $L
export OMPI_MCA_mpi_yield_when_idle=1
PINS="--pin Fcapil=0.06 --pin windReductionParam=0.28"
DBR="--pin theta_sat@glacDbr=0.3"
while read case name samples dbr; do
  for lab in asis fix3; do
    pins=""; [ $lab = fix3 ] && pins="$PINS $([ $dbr = y ] && echo $DBR)"
    $PY rerun_trials.py $case $name $samples --calibration-years --ranks 2 --jobs 1 $pins --label $lab \
      > $L/${case}_${name}_$lab.log 2>&1 &
  done
  wait
done <<END
gulkana_added calibration_1120r5b 472 y
gulkana_added calibration 459 y
gulkana_added calibration_seed43 465 y
gulkana_added calibration_seed44 385 y
gulkana_general calibration 472 y
wolverine_added calibration_1120r5b 465 y
wolverine_general calibration 473 n
END
echo "fix3 done"
