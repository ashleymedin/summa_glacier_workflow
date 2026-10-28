#!/bin/bash
# CPU-time reruns: row 7 tie on s12, row 2 air-entry on s4
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow/scratch/2026-10-29/ida_stiff
SP=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/662dfb0c-dca9-4bc0-beaa-ff5eedc7f2ab/scratchpad
B=$SP/wbase/bin/summa_sundials_mizuroute.exe; A=$SP/wair/bin/summa_sundials_mizuroute.exe
ONLY=s12 EXTRA=theta_mp=0.161 caffeinate -i ./ensemble.py c_mptie_s12 1e-5 4 1500 $B > c_mptie_s12.out 2>&1
ONLY=s12 caffeinate -i ./ensemble.py c_base_s12 1e-5 4 1500 $B > c_base_s12.out 2>&1
ONLY=s4 caffeinate -i ./ensemble.py c_base_s4 1e-5 8 1500 $B > c_base_s4.out 2>&1
ONLY=s4 caffeinate -i ./ensemble.py c_air_s4 1e-5 8 1500 $A > c_air_s4.out 2>&1
