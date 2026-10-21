#!/bin/bash
# wait for a calibration on the bucket-latflow build to finish, then rerun its picked trials on that build
c=$1; cd "$(dirname "$0")"
until grep -q -E "^PASS|^FAIL|ERROR" cal_$c.log; do sleep 60; done
grep -E "^PASS|^FAIL|ERROR|failed trials" cal_$c.log
cp cal_$c/output/wolverine_calibration.nc cal_$c/
SUMMA_EXE=$PWD/wtg/bin/summa_sundials_mizuroute.exe NPAR=4 python3 rerun.py $c
