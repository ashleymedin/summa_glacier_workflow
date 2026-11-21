#!/bin/bash
# Paper-1 Figs 3-5 (glacier.tex) and Figs 4-6 (glacier_forcing_runs.tex): general from round 6 (473, 472), added-data from
# round 5b (465, 472; same inputs, upland multiplier under round 5's cap of 3); round-5b figures kept as *.r5b.pdf.
WF=$(cd "$(dirname "$0")/../../.." && pwd)
PY=~/miniconda3/envs/glacier/bin/python
G=calibration_rerun
A=calibration_rerun_1120r5b
F=~/Research/USask/Writeups/summa_sundials_svn/glacier/figs
S=~/Research/USask/Writeups/summa_sundials_svn/coldstream/streamtemp/figs
for f in $F/wolverine_best $F/gulkana_best $F/glacier_end $S/wolverine_imagery $S/gulkana_imagery $S/glacier_area; do
  [ -e $f.r5b.pdf ] || cp $f.pdf $f.r5b.pdf
done
cd $WF
$PY plot_setup_runs.py wolverine $F/wolverine_best.pdf wolverine_added:$A:465:added wolverine_general:$G:473:general 2>&1 | tail -1
$PY plot_setup_runs.py gulkana $F/gulkana_best.pdf gulkana_added:$A:472:added gulkana_general:$G:472:general 2>&1 | tail -1
$PY plot_glacier_end.py $F/glacier_end.pdf wolverine:general:runs/wolverine_general/$G/sample_473_aligned:473 wolverine:added:runs/wolverine_added/$A/sample_465_aligned:465 \
  gulkana:general:runs/gulkana_general/$G/sample_472_aligned:472 gulkana:added:runs/gulkana_added/$A/sample_472_aligned:472 2>&1 | tail -1
cd $S || exit 1
$PY plot_glacier_imagery.py wolverine_imagery.pdf wolverine wolverine_added/$A/sample_465=added-data wolverine_general/$G/sample_473=general 2>&1 | tail -1
$PY plot_glacier_imagery.py gulkana_imagery.pdf gulkana gulkana_added/$A/sample_472=added-data gulkana_general/$G/sample_472=general 2>&1 | tail -1
$PY plot_glacier_area.py glacier_area.pdf Wolverine:wolverine_added/$A/sample_465=added-data,wolverine_general/$G/sample_473=general \
  Gulkana:gulkana_added/$A/sample_472=added-data,gulkana_general/$G/sample_472=general 2>&1 | tail -4
