#!/bin/bash
cd "$(dirname "$0")"
while pgrep -f "tolall.py be8" >/dev/null; do sleep 20; done
caffeinate -i python3 tolall.py i5 1.0d-5 8 3 /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/da728c43-a932-469d-b599-df5ce3ec3e6e/scratchpad/wtol/bin/summa_sundials_mizuroute_opt.exe > i5.out 2>&1
caffeinate -i python3 tolall.py i3 1.0d-3 8 3 /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/da728c43-a932-469d-b599-df5ce3ec3e6e/scratchpad/wtol/bin/summa_sundials_mizuroute_opt.exe > i3.out 2>&1
