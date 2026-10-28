#!/bin/bash
cd "$(dirname "$0")"
caffeinate -i python3 tolall.py d03 dflt 8 3 /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/da728c43-a932-469d-b599-df5ce3ec3e6e/scratchpad/wtol/bin/summa_sundials_mizuroute_opt.exe > d03.out 2>&1
caffeinate -i python3 tolall.py d33 dflt 8 3 /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/da728c43-a932-469d-b599-df5ce3ec3e6e/scratchpad/wcoef/bin/summa_sundials_mizuroute_opt.exe > d33.out 2>&1
