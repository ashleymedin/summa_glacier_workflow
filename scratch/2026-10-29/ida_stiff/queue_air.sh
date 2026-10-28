#!/bin/bash
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow/scratch/2026-10-29/ida_stiff
ONLY=s4 caffeinate -i ./ensemble.py c_air_s4 1e-5 8 1500 /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/662dfb0c-dca9-4bc0-beaa-ff5eedc7f2ab/scratchpad/wair/bin/summa_sundials_mizuroute.exe > c_air_s4.out 2>&1
ONLY=s4 caffeinate -i ./ensemble.py c_base2_s4 1e-5 8 1500 /private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/662dfb0c-dca9-4bc0-beaa-ff5eedc7f2ab/scratchpad/wbase/bin/summa_sundials_mizuroute.exe > c_base2_s4.out 2>&1
