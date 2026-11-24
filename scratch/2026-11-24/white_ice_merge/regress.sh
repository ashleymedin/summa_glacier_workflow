#!/bin/bash
# Eight trials over WY2006-07 of two glacier-only cases, before and after the white-ice merge, and one stream case after it.
cd "$(dirname "$0")/../../../runs"
export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH OMPI_MCA_mpi_yield_when_idle=1
for c in gulkana_general wolverine_added; do
  for d in summa summa_merge; do
    SUMMA_DIR=$HOME/Research/SummaSundials/$d nice python calibrate.py calibrate $c --search domain --population 4 --generations 2 --ranks 3 \
      --cal-end 2007-09-30 --name regress_$d < /dev/null
  done
done
SUMMA_DIR=$HOME/Research/SummaSundials/summa_merge nice python calibrate.py calibrate wolverine_stream_delta --search stream --population 4 --generations 2 --ranks 3 \
  --cal-end 2018-09-30 --name regress_summa_merge < /dev/null
