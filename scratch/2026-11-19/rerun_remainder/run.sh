#!/bin/bash
# Serial driver with a pinned trial's parameters as --param, as a failed trial's rerun.sh runs it, over ten days.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
src=/Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs/wolverine_stream_delta/calibration_r3_rerun/sample_405_delta/config.toml
mkdir -p "$here/output"
sed -e "s|^\([[:space:]]*output_path[[:space:]]*=\).*|\1 \"$here/output/\"|" \
    -e "s|^\([[:space:]]*work_path[[:space:]]*=\).*|\1 \"$here/output\"|" \
    -e "s|^\([[:space:]]*end_time[[:space:]]*=\).*|\1 \"2005-10-11 00:00\"|" "$src" > "$here/rerun.toml"
args=$(grep -E '^"[A-Za-z_@0-9]+" = \{ lower' "$src" | sed -E 's/^"([^"]+)" = \{ lower = ([^,]+),.*/--param \1 \2/' | tr '\n' ' ')
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow/runs
/Users/amedin/Research/SummaSundials/summa/bin/summa_sundials_mizuroute.exe -c "$here/rerun.toml" $args 2>&1 | tee "$here/rerun.log"
