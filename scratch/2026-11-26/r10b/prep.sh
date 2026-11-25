#!/bin/bash
# Round 10b: shadow domains whose station-corrected forcing has no rain rise above the gauges (rain_grad), and no upland snow rise (upland_snow_grad) in the cases. Nothing of round 10 is written:
# data/domain_<D>_10b links everything of domain_<D> but forcing, whose small files are copied and SUMMA_input linked, with its own station_corrected.
set -e; cd "$(dirname "$0")/../../.."; export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH; W=$PWD
for D in Wolverine Gulkana; do
  d=$(echo $D | tr A-Z a-z); s=data/domain_$D; t=data/domain_${D}_10b; [ -e $t ] && { echo "$t exists"; exit 1; }
  mkdir -p $t/forcing/SUMMA_input
  for x in attributes observations settings shapefiles; do ln -s $W/$s/$x $t/$x; done
  for x in $s/forcing/raw_data $s/forcing/raw_levels; do ln -s $W/$x $t/forcing/; done
  find $s/forcing -maxdepth 1 -type f ! -name .DS_Store -exec cp -p {} $t/forcing/ \;
  find $W/$s/forcing/SUMMA_input -maxdepth 1 -type f ! -name .DS_Store -exec ln -s {} $t/forcing/SUMMA_input/ \;
  sed -e "s#^project_dir: data/domain_$D .*#project_dir: $t#" -e '/^rain_grad:/d' domains/$d.yaml > domains/${d}_10b.yaml
  grep -q '^domain:' domains/${d}_10b.yaml || sed -i '' "s#^project_dir: .*#&\ndomain: $D#" domains/${d}_10b.yaml
  nice -n 10 python setup_glacier_domain.py domains/${d}_10b.yaml --steps forcing > runs/logs/2026-11-26r10b/forcing_$d.log 2>&1
done
