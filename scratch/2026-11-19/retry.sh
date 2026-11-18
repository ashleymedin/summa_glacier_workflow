#!/bin/zsh
# Rerun the command given every 30 min until it succeeds (queued CDS jobs resume from their saved ids).
cd "$(dirname "$0")/../.."
until "$@"; do
    echo "$(date '+%m-%d %H:%M') failed; retrying in 30 min"
    sleep 1800
done
