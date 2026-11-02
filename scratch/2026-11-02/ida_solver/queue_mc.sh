#!/bin/bash
# multi-calib with the debris baseflow fix and compact psi = 0 smoothing cherry-picked (ece1f50d), Wolverine IDA and BE, run concurrently
T="$(dirname "$0")/../../2026-10-28/ida_solver"; cd "$T"
MC=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/57e7be7a-58e3-446d-b540-98d5dbb59ca8/scratchpad/wsm3/bin/summa_sundials_mizuroute_opt.exe
export IDA_DEADBAND=0
caffeinate -i python3 tolall.py mc_wol dflt 8 3 $MC > mc_wol.out 2>&1 &
caffeinate -i python3 tolall.py mc_wol_be be 8 3 $MC > mc_wol_be.out 2>&1 &
wait
