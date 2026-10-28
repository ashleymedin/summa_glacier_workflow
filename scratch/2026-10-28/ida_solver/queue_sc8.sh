#!/bin/bash
cd "$(dirname "$0")"
export SCALED=1
CASE=bow caffeinate -i python3 tolall.py sc_bow_b8 1.0d-8 48 3 /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/da728c43-a932-469d-b599-df5ce3ec3e6e/scratchpad/wtol/bin/summa_sundials_mizuroute_opt.exe > sc_bow_b8.out 2>&1
caffeinate -i python3 tolall.py sc_i8 1.0d-8 8 3 /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/da728c43-a932-469d-b599-df5ce3ec3e6e/scratchpad/wtol/bin/summa_sundials_mizuroute_opt.exe > sc_i8.out 2>&1
