#!/bin/bash
cd "$(dirname "$0")"
export CASE=bow
for v in "be be" "b5 1.0d-5" "b3 1.0d-3" "b8 1.0d-8"; do set -- $v; caffeinate -i python3 tolall.py bow_$1 $2 48 3 /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/da728c43-a932-469d-b599-df5ce3ec3e6e/scratchpad/wtol/bin/summa_sundials_mizuroute_opt.exe > bow_$1.out 2>&1; done
