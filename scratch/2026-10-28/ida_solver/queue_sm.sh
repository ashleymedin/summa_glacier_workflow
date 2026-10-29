#!/bin/bash
# psi = 0 smoothing test (29 Oct): Bow BE/IDA and Wolverine IDA baseline and BE, with (sm) and without (bs) smoothing
cd "$(dirname "$0")"
SP=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/013bfce6-1e93-4f31-97f7-8d26c282aa89/scratchpad
SM=$SP/wsm/bin/summa_sundials_mizuroute_opt.exe; BS=$SP/wbs/bin/summa_sundials_mizuroute_opt.exe
while pgrep -f "tolall.py sm_wol" > /dev/null; do sleep 30; done
export IDA_DEADBAND=0
for v in "bs_bow_be be $BS" "sm_bow_be be $SM" "bs_bow_i dflt $BS" "sm_bow_i dflt $SM"; do set -- $v
  CASE=bow caffeinate -i python3 tolall.py $1 $2 48 3 $3 > $1.out 2>&1; done
for v in "bs_wol dflt $BS" "bs_wol_be be $BS" "sm_wol_be be $SM"; do set -- $v
  caffeinate -i python3 tolall.py $1 $2 8 3 $3 > $1.out 2>&1; done
