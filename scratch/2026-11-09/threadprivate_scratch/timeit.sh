#!/bin/sh
# alternate flag/noflag runs; print user CPU seconds per run
S=$1; sol=$2; n=$3
for i in $(seq 1 $n); do for v in flag noflag; do
  /usr/bin/time -p $S/$v/bin/summa_sundials.exe -m $S/run/fm_${v}_$sol.txt > $S/run/log_${v}_${sol}_$i.txt 2> $S/run/time_${v}_${sol}_$i.txt
  echo "$sol $v $i $(grep -E '^(real|user)' $S/run/time_${v}_${sol}_$i.txt | tr '\n' ' ')"
done; done
