#!/bin/bash
# Paper-1 Figs 3-5 (glacier.tex) and the coldstream imagery/area figures from round 9's balanced trials (merged seed fronts):
# Wolverine general 479, Gulkana general 474, Gulkana added 413 (seed 43), Wolverine added 465 (seed 42); round-6 figures kept as *.r6.pdf.
WF=$(cd "$(dirname "$0")/../../.." && pwd)
PY=~/miniconda3/envs/glacier/bin/python
S43=calibration_s43_rerun
S42=calibration_rerun
F=~/Research/USask/Writeups/summa_sundials_svn/glacier/figs
S=~/Research/USask/Writeups/summa_sundials_svn/coldstream/streamtemp/figs
for f in $F/wolverine_best $F/gulkana_best $F/glacier_end $S/wolverine_imagery $S/gulkana_imagery $S/glacier_area; do
  [ -e $f.r6.pdf ] || cp $f.pdf $f.r6.pdf
done
cd $WF
$PY plot_setup_runs.py wolverine $F/wolverine_best.pdf wolverine_added:$S42:465:added wolverine_general:$S43:479:general 2>&1 | tail -1
$PY plot_setup_runs.py gulkana $F/gulkana_best.pdf gulkana_added:$S43:413:added gulkana_general:$S43:474:general 2>&1 | tail -1
$PY plot_glacier_end.py $F/glacier_end.pdf wolverine:general:runs/wolverine_general/$S43/sample_479_aligned:479 wolverine:added:runs/wolverine_added/$S42/sample_465_aligned:465 \
  gulkana:general:runs/gulkana_general/$S43/sample_474_aligned:474 gulkana:added:runs/gulkana_added/$S43/sample_413_aligned:413 2>&1 | tail -1
cd $S || exit 1
$PY plot_glacier_imagery.py wolverine_imagery.pdf wolverine wolverine_added/$S42/sample_465=added-data wolverine_general/$S43/sample_479=general 2>&1 | tail -1
$PY plot_glacier_imagery.py gulkana_imagery.pdf gulkana gulkana_added/$S43/sample_413=added-data gulkana_general/$S43/sample_474=general 2>&1 | tail -1
$PY plot_glacier_area.py glacier_area.pdf Wolverine:wolverine_added/$S42/sample_465=added-data,wolverine_general/$S43/sample_479=general \
  Gulkana:gulkana_added/$S43/sample_413=added-data,gulkana_general/$S43/sample_474=general 2>&1 | tail -4
