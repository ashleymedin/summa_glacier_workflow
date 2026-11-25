#!/bin/bash
# The cheap lemon_stream_grus search pinned at cheap_snow's balanced trial of KGE 0.75 or more, and a one-trial check of the masked evaluation files on lemon_grus.
cd "$(dirname "$0")/../../runs"; export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH SUMMA_DIR=$HOME/Research/SummaSundials/summa_next OMPI_MCA_mpi_yield_when_idle=1
L=logs/2026-11-25; mkdir -p $L; t=$(python ../scratch/2026-11-24/lemon_night/pick.py lemon_grus/cheap_snow) || exit 1; echo "trial $t"
nice -n 5 python - > $L/eval_check.log 2>&1 <<P &
import calibrate as k, os, numpy as np, netCDF4 as nc4
R=os.path.join(k.HERE,"lemon_grus"); s=k.search_of(R+"/cheap_snow"); p=k.periods("lemon_grus"); w=R+"/eval_check"
with nc4.Dataset(k.calibration_file(R+"/cheap_snow")) as d: v={n:float(d[n][$t-1]) for n in k.searched_names(s) if n in d.variables}
k.pin_settings(R+"/summa_inputs",w+"_settings",v)
k.run_driver(w,k.config_text("lemon_grus",R,w+"_settings",w,p[0],p[3],p[2],p[3],"dds",1,1,temperature=True,search=s,pinned=v),w+"_settings",2)
with nc4.Dataset(k.calibration_file(w)) as d: print(d["objective"].target,d["objective"][0])
P
nice -n 5 python calibrate.py calibrate lemon_stream_grus --search stream --population 12 --generations 8 --ranks 3 --pin-trial calibration_pin:$t --name stream_cheap_kge75 < /dev/null > $L/stream_cheap_kge75.log 2>&1 || echo failed >> $L/stream_cheap_kge75.log
wait; echo "stream_kge75 done"
