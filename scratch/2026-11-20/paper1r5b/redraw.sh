#!/bin/bash
# Paper-1 Figs 3-5 (glacier.tex) and Figs 4-6 (glacier_forcing_runs.tex) from the round-5b balanced trials; round-4 copies kept as *.r4.pdf.
WF=$(cd "$(dirname "$0")/../../.." && pwd)
PY=~/miniconda3/envs/glacier/bin/python
R=calibration_rerun_1120r5b
F=~/Research/USask/Writeups/summa_sundials_svn/glacier/figs
S=~/Research/USask/Writeups/summa_sundials_svn/coldstream/streamtemp/figs
for f in $F/wolverine_best $F/gulkana_best $F/glacier_end $S/wolverine_imagery $S/gulkana_imagery $S/glacier_area; do
  [ -e $f.r4.pdf ] || cp $f.pdf $f.r4.pdf
done
cd $WF
$PY plot_setup_runs.py wolverine $F/wolverine_best.pdf wolverine_added:$R:465:added wolverine_general:$R:434:general 2>&1 | tail -2
$PY plot_setup_runs.py gulkana $F/gulkana_best.pdf gulkana_added:$R:472:added gulkana_general:$R:471:general 2>&1 | tail -2
$PY plot_glacier_end.py $F/glacier_end.pdf wolverine:general:runs/wolverine_general/$R/sample_434_aligned:434 wolverine:added:runs/wolverine_added/$R/sample_465_aligned:465 \
  gulkana:general:runs/gulkana_general/$R/sample_471_aligned:471 gulkana:added:runs/gulkana_added/$R/sample_472_aligned:472 2>&1 | tail -2
cd $S || exit 1
$PY plot_glacier_imagery.py wolverine_imagery.pdf wolverine wolverine_added/$R/sample_465=added-data wolverine_general/$R/sample_434=general 2>&1 | tail -1
$PY plot_glacier_imagery.py gulkana_imagery.pdf gulkana gulkana_added/$R/sample_472=added-data gulkana_general/$R/sample_471=general 2>&1 | tail -1
$PY plot_glacier_area.py glacier_area.pdf Wolverine:wolverine_added/$R/sample_465=added-data,wolverine_general/$R/sample_434=general \
  Gulkana:gulkana_added/$R/sample_472=added-data,gulkana_general/$R/sample_471=general 2>&1 | tail -8
