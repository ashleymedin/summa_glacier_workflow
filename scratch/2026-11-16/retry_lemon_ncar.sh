#!/bin/zsh
# Rerun the Lemon Creek NCAR pressure-level download every 30 min until it finishes.
cd "$(dirname "$0")/../.."
until /Users/amedin/miniconda3/envs/glacier/bin/python acquire_era5_levels.py 2004-10 2026-09 domains/lemon_creek.yaml; do
    echo "$(date '+%m-%d %H:%M') NCAR failed; retrying in 30 min"
    sleep 1800
done
