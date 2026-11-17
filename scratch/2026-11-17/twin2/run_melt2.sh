#!/bin/bash
# melt2 only, both general cases (snow2 dropped: precipElevGrad barely acts within an HRU); waits for a running grid's pid first
cd "$(dirname "$0")"
PY=~/miniconda3/envs/glacier/bin/python
export OMPI_MCA_mpi_yield_when_idle=1
[ -n "$1" ] && while kill -0 "$1" 2>/dev/null; do sleep 30; done
for c in wolverine_general gulkana_general; do
  [ -f ../../../runs/$c/twin_melt2/obs/.done ] || { $PY twin2.py truth $c melt2 && touch ../../../runs/$c/twin_melt2/obs/.done; } || { echo "truth $c melt2 failed"; continue; }
  $PY twin2.py run $c melt2 --jobs 5
  $PY twin2.py report $c melt2
done
echo all done
