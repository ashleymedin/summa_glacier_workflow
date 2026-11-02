#!/bin/bash
# paired IDA CPU check, debris baseflow fix (bf) vs multi-calib (b0), Wolverine default IDA, run concurrently
T="$(dirname "$0")/../../2026-10-28/ida_solver"; cd "$T"
SP=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/013bfce6-1e93-4f31-97f7-8d26c282aa89/scratchpad
export IDA_DEADBAND=0
caffeinate -i python3 tolall.py bfq_wol dflt 8 3 $SP/wbf/bin/summa_sundials_mizuroute_opt.exe > bfq_wol.out 2>&1 &
caffeinate -i python3 tolall.py b0q_wol dflt 8 3 $SP/wb0/bin/summa_sundials_mizuroute_opt.exe > b0q_wol.out 2>&1 &
wait
