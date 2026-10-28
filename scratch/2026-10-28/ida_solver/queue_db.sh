#!/bin/bash
# root deadband (one error weight) with Newton coefficient 0.33
cd "$(dirname "$0")"
X=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/b2242790-8a98-415d-a1af-55d7afba5666/scratchpad/wroot/bin/summa_sundials_mizuroute_opt.exe
(CASE=bow SCALED=1 caffeinate -i python3 tolall.py db_sc_bow 1.0d-3 48 3 $X > db_sc_bow.out 2>&1) &
(CASE=bow caffeinate -i python3 tolall.py db_bow dflt 48 3 $X > db_bow.out 2>&1) &
(caffeinate -i python3 tolall.py db_wol dflt 8 3 $X > db_wol.out 2>&1; SCALED=1 caffeinate -i python3 tolall.py db_sc_wol 1.0d-3 8 3 $X > db_sc_wol.out 2>&1) &
wait
