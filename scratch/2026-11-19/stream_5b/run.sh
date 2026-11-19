#!/bin/zsh
# 19-20 Nov, Paper 2: once round 5b's added-data calibrations end, the stream cases are rebuilt and respun on their inputs,
# each glacier's 5b balanced trial is rerun on them (Stage 0), and the stream-only search (Stage A) runs with every other
# parameter pinned at that trial, then is scored on the held-out years. Niced, beside the 5b general pair.
cd "$(dirname "$0")/../../.."
PY=~/miniconda3/envs/glacier/bin/python
OUT=$PWD/scratch/2026-11-19/stream_5b
export OMPI_MCA_mpi_yield_when_idle=1
NICE=(nice -n 15)

L5=runs/logs/2026-11-19r5b
for c in wolverine_added gulkana_added; do
  until grep -q "calibration written" $L5/calibrate_$c.log 2>/dev/null; do
    grep -q "exited" $L5/calibrate_$c.log 2>/dev/null && { echo "5b $c failed"; exit 1; }
    sleep 120
  done
done
echo "$(date '+%d %H:%M') 5b added pair done"
$PY - > $OUT/balanced.txt <<'EOF' || { echo "no 5b front"; exit 1; }
import sys
sys.path.insert(0, "scratch/2026-11-17/paper1")
from post_cal import picks
for case in ("wolverine_added", "gulkana_added"):
    (q, bal, mb), n = picks(case)
    print(case, bal, q, mb, n)
EOF
W=$(awk '$1=="wolverine_added"{print $2}' $OUT/balanced.txt)
G=$(awk '$1=="gulkana_added"{print $2}' $OUT/balanced.txt)
echo "balanced trials: Wolverine $W, Gulkana $G"

# Gulkana's no-fan inputs: gulkana_stream without its wetland, built beside the fan's (as stream_r3/run.sh)
$PY - <<'EOF'
import yaml
c = yaml.safe_load(open("cases.yaml"))
s = dict(c["gulkana_stream"], dest="runs/gulkana_stream_nowet")
del s["wetland"]
yaml.safe_dump({"gulkana_added": c["gulkana_added"], "gulkana_stream_nowet": s}, open("cases_nowet_tmp.yaml", "w"))
EOF
$NICE $PY build_cases.py cases.yaml wolverine_stream wolverine_stream_delta gulkana_stream > $OUT/build.log 2>&1 || { echo "build failed"; exit 1; }
$NICE $PY build_cases.py cases_nowet_tmp.yaml gulkana_stream_nowet >> $OUT/build.log 2>&1 || { echo "nowet build failed"; exit 1; }
rm cases_nowet_tmp.yaml

cd runs
rm -rf gulkana_stream/summa_inputs_nowet
mv gulkana_stream_nowet/summa_inputs gulkana_stream/summa_inputs_nowet
rm -rf gulkana_stream_nowet
for c in wolverine_stream wolverine_stream_delta; do
  $NICE $PY spinup.py $c > $OUT/spinup_$c.log 2>&1 &
done
( $NICE $PY spinup.py gulkana_stream > $OUT/spinup_gulkana_stream.log 2>&1
  mv gulkana_stream/summa_inputs gulkana_stream/summa_inputs_fan
  mv gulkana_stream/summa_inputs_nowet gulkana_stream/summa_inputs
  $NICE $PY spinup.py gulkana_stream > $OUT/spinup_gulkana_stream_nowet.log 2>&1
  mv gulkana_stream/summa_inputs gulkana_stream/summa_inputs_nowet
  mv gulkana_stream/summa_inputs_fan gulkana_stream/summa_inputs ) &
wait
echo "$(date '+%d %H:%M') stream cases rebuilt and spun up"

for pair in wolverine_stream:wolverine_added wolverine_stream_delta:wolverine_added gulkana_stream:gulkana_added; do
  c=${pair%%:*} p=${pair##*:}
  rm -rf $c/calibration_5b
  mkdir -p $c/calibration_5b/output
  cp $p/calibration/config.toml $c/calibration_5b/
  cp $p/calibration/output/*_calibration.nc $c/calibration_5b/output/
done

# Stage 0: the balanced trials on the stream cases, nothing searched
X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow)
$NICE $PY rerun_trials.py wolverine_stream calibration_5b $W $X --set wetlandMaxArea=0 --label nolake > $OUT/w_nolake.log 2>&1 &
$NICE $PY rerun_trials.py wolverine_stream calibration_5b $W $X --label lake > $OUT/w_lake.log 2>&1 &
$NICE $PY rerun_trials.py wolverine_stream_delta calibration_5b $W $X --label delta > $OUT/w_delta.log 2>&1 &
$NICE $PY rerun_trials.py gulkana_stream calibration_5b $G $X --inputs gulkana_stream/summa_inputs_nowet --label nowet > $OUT/g_nowet.log 2>&1 &
$NICE $PY rerun_trials.py gulkana_stream calibration_5b $G $X --label fan > $OUT/g_fan.log 2>&1 &
wait
echo "$(date '+%d %H:%M') stage 0 done"

# Stage A: the stream's own parameters only, Wolverine first (its temperature runs 2016-2026)
$NICE $PY calibrate.py calibrate wolverine_stream_delta --search stream --pin-trial calibration_5b:$W \
  --population 12 --generations 6 --ranks 3 --name stream_a > $OUT/stream_a_wolverine.log 2>&1
$NICE $PY calibrate.py evaluate wolverine_stream_delta --name stream_a --ranks 2 --jobs 1 >> $OUT/stream_a_wolverine.log 2>&1
echo "$(date '+%d %H:%M') stage A Wolverine done"
$NICE $PY calibrate.py calibrate gulkana_stream --search stream --pin-trial calibration_5b:$G \
  --population 12 --generations 6 --ranks 3 --name stream_a > $OUT/stream_a_gulkana.log 2>&1
$NICE $PY calibrate.py evaluate gulkana_stream --name stream_a --ranks 2 --jobs 1 >> $OUT/stream_a_gulkana.log 2>&1
echo "$(date '+%d %H:%M') stage A Gulkana done"
