#!/bin/bash
# After round 6's general pair: if Gulkana general's balanced trial reaches round 4 (calibration KGE >= 0.88 and WGMS RMSE
# <= 750 mm; round 4 0.909 and 686), run round 6's added pair; otherwise round 7, the upland soil searched in all four
# cases (search domain_soil, multipliers 0.2-5), round 6 kept as calibration*_1120r6.
D=$(cd "$(dirname "$0")" && pwd)
cd "$D/../../../runs"
PY=~/miniconda3/envs/glacier/bin/python
until grep -q "round 6 done" logs/2026-11-20r6/run.log 2>/dev/null; do sleep 120; done
balanced() { grep -o "balanced [0-9]*" logs/$1/post_driver_$2.log | awk '{print $2}'; }
for c in wolverine_general gulkana_general; do $PY $D/scores.py $c calibration_rerun $(balanced 2026-11-20r6 $c); done | tee $D/scores_r6_general.txt
read kge wgms < <(awk '/gulkana_general .* discharge/{k=$4} /gulkana_general .* wgms_amce/{w=$4} END{print k, w}' $D/scores_r6_general.txt)
if awk -v k=$kge -v w=$wgms 'BEGIN{exit !(k >= 0.88 && w <= 750)}'; then
  echo "decision: round 6 kept (Gulkana general KGE $kge, WGMS $wgms); running the added pair"
  ROUND=2026-11-20r6 bash $D/run.sh "wolverine_added gulkana_added"
else
  echo "decision: round 7 (Gulkana general KGE $kge, WGMS $wgms)"
  for c in wolverine_general gulkana_general; do for d in calibration calibration_evaluation calibration_rerun; do mv $c/$d $c/${d}_1120r6; done; done
  mkdir -p logs/2026-11-20r7
  SEARCH=domain_soil ROUND=2026-11-20r7 bash $D/run.sh "wolverine_general gulkana_general" "wolverine_added gulkana_added"
fi
echo "next done"
