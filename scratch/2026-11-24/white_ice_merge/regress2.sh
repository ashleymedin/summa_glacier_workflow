#!/bin/bash
# The glacier cases again, both builds without fused multiply-add (-ffp-contract=off): bit-identical if only roundoff differed.
cd "$(dirname "$0")/../../../runs"
export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH OMPI_MCA_mpi_yield_when_idle=1
for c in wolverine_added gulkana_added; do for d in summa_base summa_mtest; do
  SUMMA_DIR=$HOME/Research/SummaSundials/$d nice python calibrate.py calibrate $c --search domain --population 4 --generations 2 --ranks 3 \
    --cal-end 2007-09-30 --name regress_$d < /dev/null
done; done
