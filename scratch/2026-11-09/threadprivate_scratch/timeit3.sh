#!/bin/sh
# alternate base/new2 runs; user CPU seconds and peak resident memory per run
S=$1; sol=$2; n=$3
for i in $(seq 1 $n); do for v in base new2; do
  /usr/bin/time -l $S/$v/bin/summa_sundials.exe -m $S/run2/fm_${v}_$sol.txt > /dev/null 2> $S/run2/t3_${v}_${sol}_$i.txt
  echo "$sol $v $i user $(grep -E ' user ' $S/run2/t3_${v}_${sol}_$i.txt | awk '{print $3}') maxrss $(grep 'maximum resident' $S/run2/t3_${v}_${sol}_$i.txt | awk '{print $1}')"
done; done
