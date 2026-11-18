#!/bin/zsh
# Rerun the Lemon Creek NCAR single-level download into forcing/raw_data_ncar every 30 min until it finishes.
cd "$(dirname "$0")/../.."
until /Users/amedin/miniconda3/envs/glacier/bin/python acquire_era5.py 2004-10 2026-09 domains/lemon_creek.yaml --source ncar --out data/domain_LemonCreek/forcing/raw_data_ncar; do
    echo "$(date '+%m-%d %H:%M') NCAR failed; retrying in 30 min"
    sleep 1800
done
