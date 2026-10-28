#!/bin/bash
# row 7 macropore: default, macropore off, theta_mp tied 0.1 below theta_sat
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow/scratch/2026-10-29/ida_stiff
X=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/662dfb0c-dca9-4bc0-beaa-ff5eedc7f2ab/scratchpad/wbase/bin/summa_sundials_mizuroute.exe
caffeinate -i ./ensemble.py base 1e-5 4 900 $X > base.out 2>&1
EXTRA=theta_mp=0.6 caffeinate -i ./ensemble.py mpoff 1e-5 4 900 $X > mpoff.out 2>&1
ONLY=s2 EXTRA=theta_mp=0.336 caffeinate -i ./ensemble.py mptie_s2 1e-5 4 900 $X > mptie_s2.out 2>&1
ONLY=s4 EXTRA=theta_mp=0.415 caffeinate -i ./ensemble.py mptie_s4 1e-5 4 900 $X > mptie_s4.out 2>&1
ONLY=s12 EXTRA=theta_mp=0.161 caffeinate -i ./ensemble.py mptie_s12 1e-5 4 900 $X > mptie_s12.out 2>&1
