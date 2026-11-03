#!/bin/bash
export SUMMA_DIR=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/28cc11f8-de39-47db-a9e8-554c4eb8514f/scratchpad/wt
P=/Users/amedin/miniconda3/envs/glacier/bin/python; W=/Users/amedin/Research/SummaSundials/summa_glacier_workflow
cd $W/runs
PINS=(--pin windExposure=0.77 --pin glacierWindFactor=1 --pin glacierTempReduction=1.3 --pin frozenPrecipMultip=1 --pin tempCritRain=273.16 --pin tempRangeTimestep=2)
$P rerun_trials.py gulkana_corrected calibration_paper1 384 "${PINS[@]}" --extra scalarSnowAlbedo --extra scalarGroundAlbedo --inputs $W/runs/gulkana_added/summa_inputs --forcing $W/data/domain_Gulkana/forcing/SUMMA_input/station_corrected --label wilson > $W/scratch/2026-11-03/rerun_g384wilson.log 2>&1
