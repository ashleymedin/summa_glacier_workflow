#!/bin/bash
# compact psi = 0 smoothing (sm3, branch psi-smooth3) vs the debris baseflow fix alone (bf_wol*) and multi-calib (b0_bow*) from queue_sm2.sh
T="$(dirname "$0")/../../2026-10-28/ida_solver"; cd "$T"
SM=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/57e7be7a-58e3-446d-b540-98d5dbb59ca8/scratchpad/wsm3/bin/summa_sundials_mizuroute_opt.exe
export IDA_DEADBAND=0
for v in "sm3_wol dflt" "sm3_wol_be be"; do set -- $v
  caffeinate -i python3 tolall.py $1 $2 8 3 $SM > $1.out 2>&1; done
for v in "sm3_bow_be be" "sm3_bow_i dflt"; do set -- $v
  CASE=bow caffeinate -i python3 tolall.py $1 $2 48 3 $SM > $1.out 2>&1; done
