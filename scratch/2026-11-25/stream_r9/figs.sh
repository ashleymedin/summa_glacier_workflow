#!/bin/bash
# Figs 2, 3 and 7 of glacier_forcing_runs.tex from round 9's balanced trials and run.sh's stream-case reruns (Figs 4-6: paper1r9/redraw.sh);
# the round-3 figures kept as *.r3.pdf, figure 7's table rows in tab_lake_heat.tex.
cd "$(dirname "$0")/../../.."; PY=/Users/amedin/miniconda3/envs/glacier/bin/python; W=$PWD/scratch/2026-11-25/stream_r9
F=~/Research/USask/Writeups/summa_sundials_svn/coldstream/streamtemp/figs; R=calibration_r9_rerun
r9() { [ -d runs/$1/$2_1125r9 ] && echo $2_1125r9 || echo $2; }  # round 9's folders once round 10 has started on the case
for f in wolverine_best gulkana_best lake_heat; do [ -e $F/$f.r3.pdf ] || cp -p $F/$f.pdf $F/$f.r3.pdf; done
$PY plot_setup_runs.py wolverine $F/wolverine_best.pdf wolverine_added:$(r9 wolverine_added calibration_rerun):465:added wolverine_general:$(r9 wolverine_general calibration_s43_rerun):479:general \
  temp:wolverine_stream_delta:$R:465_nolake:"added, no lake" temp:wolverine_stream_delta:$R:465_delta:"added, lake and delta" temp:wolverine_stream_delta:$R:465_fetch:"added, lake"
$PY plot_setup_runs.py gulkana $F/gulkana_best.pdf gulkana_added:$(r9 gulkana_added calibration_s43_rerun):413:added gulkana_general:$(r9 gulkana_general calibration_s43_rerun):474:general \
  temp:gulkana_stream:$R:413_nowet:"added, no fan" temp:gulkana_stream:$R:413_fan:"added, fan" temp:gulkana_stream:$R:413_scale:"added, fan with flow"
D=data/domain_Wolverine/observations
PYTHONPATH=scratch/2026-11-13 $PY $W/lake_heat.py runs/wolverine_stream_delta/$R $D/calibration $D/lake_area $F/lake_heat.pdf $W/tab_lake_heat.tex
