#!/bin/bash
# debris lateral flow stops at theta_res (bf) vs multi-calib (b0): Wolverine BE and IDA default, 8 trials, 3 ranks
T="$(dirname "$0")/../../2026-10-28/ida_solver"; cd "$T"
SP=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/013bfce6-1e93-4f31-97f7-8d26c282aa89/scratchpad
BF=$SP/wbf/bin/summa_sundials_mizuroute_opt.exe; B0=$SP/wb0/bin/summa_sundials_mizuroute_opt.exe
export IDA_DEADBAND=0
for v in "bf_wol_be be $BF" "b0_wol_be be $B0" "bf_wol dflt $BF" "b0_wol dflt $B0"; do set -- $v
  caffeinate -i python3 tolall.py $1 $2 8 3 $3 > $1.out 2>&1; done
