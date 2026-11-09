#!/bin/sh
# alternate base/new runs without malloc counting; print user CPU seconds per run
S=$1; sol=$2; n=$3
for i in $(seq 1 $n); do for v in base new; do
  /usr/bin/time -p $S/$v/bin/summa_sundials.exe -m $S/run2/fm_${v}_$sol.txt > /dev/null 2> $S/run2/t_${v}_${sol}_$i.txt
  echo "$sol $v $i $(grep -E '^user' $S/run2/t_${v}_${sol}_$i.txt)"
done; done
