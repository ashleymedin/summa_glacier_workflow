#!/bin/bash
# Round 5's general pair, once the added pair, the general rebuild (slowed melt-out bed) and its screening reruns are done.
cd "$(dirname "$0")/../../../runs"
L=logs/2026-11-19r5
until grep -q "done wolverine_added gulkana_added" $L/run_added.log 2>/dev/null && grep -q "screen done" $L/screen.log 2>/dev/null; do sleep 120; done
bash ../scratch/2026-11-19/paper1r5/run.sh "wolverine_general gulkana_general"
