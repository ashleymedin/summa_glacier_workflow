#!/bin/bash
# psi = 0 smoothing on top of the debris baseflow fix (sm2) vs the fix alone (bf, Wolverine) or multi-calib (b0, Bow, no glacier)
T="$(dirname "$0")/../../2026-10-28/ida_solver"; cd "$T"
SP=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/013bfce6-1e93-4f31-97f7-8d26c282aa89/scratchpad
SM=$SP/wsm2/bin/summa_sundials_mizuroute_opt.exe; B0=$SP/wb0/bin/summa_sundials_mizuroute_opt.exe
while pgrep -f "queue_bf.sh" > /dev/null; do sleep 30; done
export IDA_DEADBAND=0
for v in "sm2_wol dflt $SM" "sm2_wol_be be $SM"; do set -- $v
  caffeinate -i python3 tolall.py $1 $2 8 3 $3 > $1.out 2>&1; done
for v in "b0_bow_be be $B0" "sm2_bow_be be $SM" "b0_bow_i dflt $B0" "sm2_bow_i dflt $SM"; do set -- $v
  CASE=bow caffeinate -i python3 tolall.py $1 $2 48 3 $3 > $1.out 2>&1; done
