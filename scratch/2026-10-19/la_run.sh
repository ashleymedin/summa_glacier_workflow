#!/bin/bash
# lake-area scans, one process per year
cd /Users/amedin/Research/SummaSundials/summa_glacier_workflow
S=/private/tmp/claude-598/-Users-amedin-Research-SummaSundials-summa/e7b19ecd-74a9-45a0-aca9-42b7b0e01d99/scratchpad/la
P=~/miniconda3/envs/modflow6/bin/python
for y in 2008 2009 2010 2011 2012 2013 2014 2015; do
  $P acquire_lake_area.py -148.918 60.3720 -148.905 60.3775 $y-01-01 $y-12-31 $S/ls_$y.csv --source landsat --usgs-site 15236900 > $S/ls_$y.log 2>&1 &
done
for y in 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025; do
  $P acquire_lake_area.py -148.918 60.3720 -148.905 60.3775 $y-01-01 $y-12-31 $S/s2_$y.csv --usgs-site 15236900 > $S/s2_$y.log 2>&1 &
done
wait
