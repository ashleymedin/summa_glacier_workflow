#!/bin/bash
# The sensitivity screen on the other three setups once Wolverine general's is done; run under caffeinate -ims.
cd "$(dirname "$0")"
export OMPI_MCA_mpi_yield_when_idle=1
PY=/Users/amedin/miniconda3/envs/glacier/bin/python
while pgrep -f "screen.py run wolverine_general" > /dev/null; do sleep 60; done
for c in gulkana_general wolverine_added gulkana_added; do
  $PY screen.py run $c --n 100 --jobs 9 > screen_$c.log 2>&1
done
