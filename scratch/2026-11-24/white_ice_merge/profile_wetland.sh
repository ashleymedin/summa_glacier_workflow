#!/bin/bash
# Samples (macOS `sample`) a running calibration's busiest worker: profile_wetland.sh <config substring> <out dir> [gap s] [sample s], until it ends.
key=$1; out=$2; gap=${3:-120}; dur=${4:-20}; mkdir -p $out; n=0
while true; do
  p=$(ps -axo pid,pcpu,command | grep "summa_sundials_mizuroute_opt.exe -c" | grep -F "$key" | grep -v -e grep -e prterun -e profile_wetland | sort -k2 -nr | awk 'NR==1{print $1}')
  [ -z "$p" ] && { [ $n -gt 0 ] && break; sleep 20; continue; }
  sample $p $dur -file $out/prof_$(printf %03d $n).txt > /dev/null 2>&1; n=$((n+1)); sleep $gap
done
echo "$n samples in $out"
