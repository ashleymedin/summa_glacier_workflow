#!/bin/zsh
# 18 Nov: the stream cases rebuilt and respun on the round-3 inputs, and the round-3 added-data trials (Wolverine 405,
# Gulkana 467) rerun on them for panel (e) of wolverine_best/gulkana_best: Wolverine with no lake, the settling lake and
# the delta above it; Gulkana with no fan, the fan as built and the fan whose wetted area follows its flow. Every reach
# falls from the modelled glacier front (outlet_elevation in cases.yaml).
cd "$(dirname "$0")/../../.."
PY=~/miniconda3/envs/glacier/bin/python
export OMPI_MCA_mpi_yield_when_idle=1
set -e

# Gulkana's no-fan inputs: gulkana_stream without its wetland, built as a case of its own and kept beside the fan's
NOWET=cases_nowet_tmp.yaml
$PY - <<'EOF'
import yaml
c = yaml.safe_load(open("cases.yaml"))
s = dict(c["gulkana_stream"], dest="runs/gulkana_stream_nowet")
del s["wetland"]
yaml.safe_dump({"gulkana_added": c["gulkana_added"], "gulkana_stream_nowet": s}, open("cases_nowet_tmp.yaml", "w"))
EOF
$PY build_cases.py cases.yaml wolverine_stream wolverine_stream_delta gulkana_stream
$PY build_cases.py $NOWET gulkana_stream_nowet
rm $NOWET

cd runs
rm -rf gulkana_stream/summa_inputs_nowet
mv gulkana_stream_nowet/summa_inputs gulkana_stream/summa_inputs_nowet
rm -rf gulkana_stream_nowet
for c in wolverine_stream wolverine_stream_delta; do
  $PY spinup.py $c > logs/spinup_${c}_r3.log 2>&1 &
done
# spinup.py reads the case's own summa_inputs and cases.yaml entry, so the no-fan inputs take the fan's place for theirs
( $PY spinup.py gulkana_stream > logs/spinup_gulkana_stream_r3.log 2>&1
  mv gulkana_stream/summa_inputs gulkana_stream/summa_inputs_fan
  mv gulkana_stream/summa_inputs_nowet gulkana_stream/summa_inputs
  $PY spinup.py gulkana_stream > logs/spinup_gulkana_stream_nowet_r3.log 2>&1
  mv gulkana_stream/summa_inputs gulkana_stream/summa_inputs_nowet
  mv gulkana_stream/summa_inputs_fan gulkana_stream/summa_inputs ) &
wait

# each stream case reads the round-3 trials of its parent's calibration
for pair in wolverine_stream:wolverine_added wolverine_stream_delta:wolverine_added gulkana_stream:gulkana_added; do
  c=${pair%%:*} p=${pair##*:}
  rm -rf $c/calibration_r3
  mkdir -p $c/calibration_r3/output
  cp $p/calibration/config.toml $c/calibration_r3/
  cp $p/calibration/output/*_calibration.nc $c/calibration_r3/output/
done

X=(--extra scalarStreamTemp --extra scalarStreamOutflow --extra scalarStreamLatInflow)
$PY rerun_trials.py wolverine_stream calibration_r3 405 $X --set wetlandMaxArea=0 --label nolake > ../scratch/2026-11-18/stream_r3/w_nolake.log 2>&1 &
$PY rerun_trials.py wolverine_stream calibration_r3 405 $X --label lake > ../scratch/2026-11-18/stream_r3/w_lake.log 2>&1 &
$PY rerun_trials.py wolverine_stream_delta calibration_r3 405 $X --label delta > ../scratch/2026-11-18/stream_r3/w_delta.log 2>&1 &
wait
$PY rerun_trials.py gulkana_stream calibration_r3 467 $X --inputs gulkana_stream/summa_inputs_nowet --label nowet > ../scratch/2026-11-18/stream_r3/g_nowet.log 2>&1 &
$PY rerun_trials.py gulkana_stream calibration_r3 467 $X --label fan > ../scratch/2026-11-18/stream_r3/g_fan.log 2>&1 &
$PY rerun_trials.py gulkana_stream calibration_r3 467 $X --set wetlandMaxArea=40000 --set wetlandFlatArea=53000 --label scale > ../scratch/2026-11-18/stream_r3/g_scale.log 2>&1 &
wait
echo all done
