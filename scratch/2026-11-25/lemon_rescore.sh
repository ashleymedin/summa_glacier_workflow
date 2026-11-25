#!/bin/bash
# Four lemon_grus/score_2006_22 members rerun on the masked windows that lemon_grus_snow was calibrated and evaluated on (cal: discharge WY2006-15; eval: discharge WY2016-20, balances WY2023-26), so the upland snow case has a like-for-like control.
cd "$(dirname "$0")/../../runs"; export PATH=/Users/amedin/miniconda3/envs/glacier/bin:$PATH SUMMA_DIR=$HOME/Research/SummaSundials/summa_next OMPI_MCA_mpi_yield_when_idle=1
nice -n 10 python - <<'P'
import calibrate as k, os, numpy as np, netCDF4 as nc4
C="lemon_grus"; R=os.path.join(k.HERE,C); s=k.search_of(R+"/score_2006_22"); p=k.periods(C)
with nc4.Dataset(k.calibration_file(R+"/score_2006_22")) as d:
    o=np.ma.filled(d["objective"][:].astype(float),np.nan); T=[88,40,70,int(np.nanargmax(o[:,0]))+1]
    V={t:{n:float(d[n][t-1]) for n in k.searched_names(s) if n in d.variables} for t in T}
for t in T:
    w=R+f"/rescore_2006_22/sample_{t}"; k.pin_settings(R+"/summa_inputs",w+"_settings",V[t])
    for name,a in (("cal","dds"),("eval","dds")):
        c=k.config_text(C,R,w+"_settings",w+"_"+name,p[0],p[1] if name=="cal" else p[3],p[0] if name=="cal" else p[2],p[1] if name=="cal" else p[3],a,1,1,temperature=True,search=s,pinned=V[t])
        if name=="cal": c=c.replace("daily_flow_eval.nc","daily_flow_cal.nc").replace("seasonal_2006_eval.nc","seasonal_2006.nc")  # discharge on the calibration mask
        k.run_driver(w+"_"+name,c,w+"_settings",2)
        with nc4.Dataset(k.calibration_file(w+"_"+name)) as d: print(t,name,d["objective"].target,d["objective"][0],flush=True)
P
echo "rescore done $(date)"
