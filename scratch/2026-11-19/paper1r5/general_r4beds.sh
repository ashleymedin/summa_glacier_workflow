#!/bin/bash
# Round 5's general pair on round 4's general domains (slowed melt-out dropped), once the added pair is done.
cd "$(dirname "$0")/../../../runs"
until grep -q "done wolverine_added gulkana_added" logs/2026-11-19r5/run_added.log 2>/dev/null; do sleep 120; done
bash ../scratch/2026-11-19/paper1r5/run.sh "wolverine_general gulkana_general"
