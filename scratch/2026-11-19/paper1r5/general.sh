#!/bin/bash
# Round 5's general pair: both general domains rebuilt (slowed melt-out on the lowest quarter), round 4's trials screened on them,
# then the pair calibrated once the added pair is done.
cd "$(dirname "$0")/../../.."
L=runs/logs/2026-11-19r5
bash scratch/2026-11-19/gulkana_slow/rebuild.sh > $L/rebuild_q25.log 2>&1
grep -q "rebuild done" $L/rebuild_q25.log || exit 1
bash scratch/2026-11-19/gulkana_slow/screen.sh > $L/screen_q25.log 2>&1
cd runs
PY=~/miniconda3/envs/glacier/bin/python
for b in gulkana wolverine; do
  s=$([ $b = gulkana ] && echo 440 || echo 465)
  $PY ../compare_glacier_change.py ../domains/${b}_general.yaml ${b}_general/calibration_1119r4_rerun/sample_${s}_slowed --observations ../domains/$b.yaml > logs/2026-11-19r5/area_${b}_general_slowed.log 2>&1
done
echo "screen q25 done"
until grep -q "done wolverine_added gulkana_added" logs/2026-11-19r5/run_added.log 2>/dev/null; do sleep 120; done
bash ../scratch/2026-11-19/paper1r5/run.sh "wolverine_general gulkana_general"
