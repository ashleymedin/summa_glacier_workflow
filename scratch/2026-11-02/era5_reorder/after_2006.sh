#!/bin/bash
# Once Jul-Dec 2006 ERA5 is in: remap all four domains, refit the all-years station correction, build the four study cases.
set -e
W=/Users/amedin/Research/SummaSundials/summa_glacier_workflow; P=/Users/amedin/miniconda3/envs/glacier/bin/python
L=$W/scratch/2026-11-02/era5_reorder/after_2006.log
cd $W
until [ -f data/domain_Gulkana/forcing/raw_data/domain_Gulkana_ERA5_merged_200612.nc ] && [ -f data/domain_Wolverine/forcing/raw_data/domain_Wolverine_ERA5_merged_200612.nc ]; do sleep 120; done
sleep 30
echo "$(date '+%F %T') 2006 in" | tee $L
for y in wolverine wolverine_general gulkana gulkana_general; do $P remap_forcing.py domains/$y.yaml >> $L 2>&1; echo "remapped $y"; done
for y in wolverine gulkana; do $P setup_glacier_domain.py domains/$y.yaml --steps forcing >> $L 2>&1; echo "corrected $y: $(grep -h 'precipElevGrad' $L | tail -1)"; done
$P build_cases.py cases.yaml wolverine_general wolverine_added gulkana_general gulkana_added >> $L 2>&1
echo "$(date '+%F %T') cases built" | tee -a $L
