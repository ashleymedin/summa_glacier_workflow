#!/bin/bash
# Times base and snow-balance-fix builds on this trial and on default parameters, full calibration period.
here="$(cd "$(dirname "$0")" && pwd)"; cd "$here"
BASE=/Users/amedin/Research/SummaSundials/summa/bin/summa_sundials.exe
FIX=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/c82a917c-ca22-4a7c-9a2c-a85c9cebdb9e/scratchpad/wt/bin/summa_sundials.exe
PARAMS=$(sed -n 's/^  --param \(.*\) \\$/--param \1/p' rerun.sh | tr '\n' ' ')
for exe in FIX BASE; do
  for p in default trial; do
    args=""; [ $p = trial ] && args="$PARAMS"
    /usr/bin/time -p ${!exe} -c full.toml $args > cost_${exe}_${p}.log 2>&1
    echo "$exe $p $(grep '^real' cost_${exe}_${p}.log) $(grep -c 'FORTRAN STOP: finished simulation successfully' cost_${exe}_${p}.log)"
  done
done
