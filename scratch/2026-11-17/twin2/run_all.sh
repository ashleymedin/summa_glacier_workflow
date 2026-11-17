#!/bin/bash
# truths, then the 6 x 6 grids at four splits, for melt2 and snow2 on both general cases
cd "$(dirname "$0")"
PY=~/miniconda3/envs/glacier/bin/python
export OMPI_MCA_mpi_yield_when_idle=1
for c in wolverine_general gulkana_general; do
  for e in melt2 snow2; do
    [ -f ../../../runs/$c/twin_$e/obs/.done ] || { $PY twin2.py truth $c $e && touch ../../../runs/$c/twin_$e/obs/.done; } || { echo "truth $c $e failed"; continue; }
    $PY twin2.py run $c $e --jobs 5
    $PY twin2.py report $c $e
  done
done
echo all done
