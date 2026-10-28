#!/bin/bash
cd "$(dirname "$0")"
CASE=bow caffeinate -i python3 tolall.py s6_bow_be be 48 3 /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/da728c43-a932-469d-b599-df5ce3ec3e6e/scratchpad/wstab/bin/summa_sundials_mizuroute_opt.exe > s6_bow_be.out 2>&1
CASE=bow caffeinate -i python3 tolall.py s6_bow_b3 1.0d-3 48 3 /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/da728c43-a932-469d-b599-df5ce3ec3e6e/scratchpad/wstab/bin/summa_sundials_mizuroute_opt.exe > s6_bow_b3.out 2>&1
caffeinate -i python3 tolall.py s6_be8 be 8 3 /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/da728c43-a932-469d-b599-df5ce3ec3e6e/scratchpad/wstab/bin/summa_sundials_mizuroute_opt.exe > s6_be8.out 2>&1
caffeinate -i python3 tolall.py s6_i3 1.0d-3 8 3 /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/da728c43-a932-469d-b599-df5ce3ec3e6e/scratchpad/wstab/bin/summa_sundials_mizuroute_opt.exe > s6_i3.out 2>&1
